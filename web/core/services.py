"""Lógica de negocio del peaje: inferencia, tarifas, registro de pasos y estados de placa."""
import time
import uuid
from datetime import timedelta
from decimal import Decimal

import requests
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db.models import Sum
from django.utils import timezone

from . import placas
from .models import Ajuste, Alerta, Paso, Tarifa, Vehiculo
from .realtime import emitir


class InferenciaError(Exception):
    pass


# --------------------------------------------------------------------------
# Inferencia (RunPod / Colab). Solo se usa INFERENCE_URL de la configuración.
# Contrato esperado de POST {INFERENCE_URL}/predict (multipart, campo "file"):
#   {"placa": {"texto": "2481KLM", "confianza": 0.91, "bbox": [x1,y1,x2,y2]},
#    "vehiculo": {"categoria": "camion", "confianza": 0.88},
#    "ejes": 3, "keypoints": [[x,y,conf],...], "latencia_ms": 412.3}
# --------------------------------------------------------------------------
def _ajuste(clave):
    a = Ajuste.objects.filter(clave=clave).first()
    return a.valor if a else None


def inference_url():
    """URL vigente: la guardada desde el panel; si no hay, la del .env (INFERENCE_URL)."""
    v = _ajuste("inference_url")
    return (v if v else settings.INFERENCE_URL).rstrip("/")


def inference_key():
    v = _ajuste("inference_api_key")
    return v if v is not None else settings.INFERENCE_API_KEY


def url_permitida(url):
    """La rúbrica da 0 por localhost, IPs privadas o túneles a equipos personales."""
    import ipaddress
    from urllib.parse import urlparse
    p = urlparse(url)
    if p.scheme not in ("http", "https") or not p.hostname:
        return "La URL debe empezar con https:// y tener un dominio."
    host = p.hostname.lower()
    if host == "localhost" or host.endswith(".local"):
        return "No se permite localhost."
    try:
        ip = ipaddress.ip_address(host)
        if ip.is_private or ip.is_loopback or ip.is_link_local:
            return "No se permiten IPs privadas o locales."
    except ValueError:
        pass
    return None


def _headers():
    h = {"ngrok-skip-browser-warning": "1"}    # evita la página intermedia de ngrok si se usa ese túnel
    if inference_key():
        h["X-API-Key"] = inference_key()
    return h


def inferir(imagen_bytes, nombre="frame.jpg"):
    url = inference_url()
    if not url:
        raise InferenciaError("El endpoint de inferencia no está configurado (Configuración del panel o INFERENCE_URL)")
    t0 = time.perf_counter()
    try:
        r = requests.post(
            f"{url}/predict",
            files={"file": (nombre, imagen_bytes, "image/jpeg")},
            headers=_headers(),
            timeout=settings.INFERENCE_TIMEOUT,
        )
        r.raise_for_status()
        data = r.json()
    except (requests.RequestException, ValueError) as e:
        raise InferenciaError(f"Endpoint de inferencia no responde: {e}") from e
    placa = data.get("placa") or {}
    veh = data.get("vehiculo") or {}
    return {
        "placa_leida": placa.get("texto") or "",
        "confianza": float(placa.get("confianza") or 0),
        "categoria": veh.get("categoria") or "",
        "ejes": int(data.get("ejes") or 0),
        "latencia_ms": data.get("latencia_ms") or round((time.perf_counter() - t0) * 1000, 1),
        "latencia_total_ms": round((time.perf_counter() - t0) * 1000, 1),
    }


def estado_inferencia():
    """Para la página 'Estado' del panel. Comprueba que responda Y que la clave sea la correcta."""
    url = inference_url()
    if not url:
        return {"ok": False, "detalle": "Endpoint no configurado", "url": ""}
    t0 = time.perf_counter()
    try:
        r = requests.get(f"{url}/health", headers=_headers(), timeout=8)
        ms = round((time.perf_counter() - t0) * 1000, 1)
        if r.status_code == 401:
            return {"ok": False, "detalle": "El endpoint responde pero rechaza la API key (revisar la clave)",
                    "latencia_ms": ms, "url": url}
        return {"ok": r.ok, "detalle": f"HTTP {r.status_code}", "latencia_ms": ms, "url": url,
                "info": r.json() if r.ok else None}
    except (requests.RequestException, ValueError) as e:
        return {"ok": False, "detalle": str(e)[:200], "url": url}


# --------------------------------------------------------------------------
# Tarifas
# --------------------------------------------------------------------------
def calcular_tarifa(categoria, ejes):
    """Busca (categoría, ejes) exacto; si no, (categoría, 0); si no, la de mayor ejes <= ejes."""
    qs = Tarifa.objects.filter(categoria=categoria)
    t = qs.filter(ejes=ejes).first() or qs.filter(ejes=0).first()
    if t is None and ejes:
        t = qs.filter(ejes__lte=ejes).order_by("-ejes").first() or qs.order_by("-ejes").first()
    return t.monto if t else Decimal("0")


# --------------------------------------------------------------------------
# Estados de placa (los 4 del enunciado)
# --------------------------------------------------------------------------
ESTADO_CON_PASO = "registrada_con_paso"
ESTADO_SIN_PASO = "registrada_sin_paso"
ESTADO_NO_REGISTRADA = "identificada_no_registrada"
ESTADO_NO_EXISTE = "no_existe"


def serializar_paso(p):
    return {
        "id": p.id,
        "placa": p.placa_normalizada,
        "placa_leida": p.placa_leida,
        "confianza_ocr": p.confianza_ocr,
        "categoria": p.categoria_detectada,
        "ejes": p.ejes_detectados,
        "monto": str(p.monto),
        "caseta_id": p.caseta_id,
        "caseta": p.caseta.nombre,
        "estado": p.estado,
        "imagen_url": p.imagen_url,
        "latencia_ms": p.latencia_ms,
        "created_at": timezone.localtime(p.created_at).isoformat(),
    }


def estado_de_placa(texto):
    """Consulta una placa y devuelve su estado. Usa SOLO datos de la BD."""
    placa = placas.normalizar(texto)
    if not placas.es_valida(placa):
        # Intenta corregir confusiones de OCR antes de rendirse
        corregida = placas.corregir_ocr(placa)
        if placas.es_valida(corregida):
            placa_original, placa = placa, corregida
        else:
            return {"estado": "formato_invalido", "placa": placa,
                    "mensaje": "El formato no corresponde a una placa válida (ej. 2481KLM)."}
    else:
        placa_original = placa

    veh = Vehiculo.objects.filter(placa=placa).first()
    pasos = Paso.objects.filter(placa_normalizada=placa).select_related("caseta")
    registradas = list(Vehiculo.objects.values_list("placa", flat=True))
    sugerencias = placas.sugerir(placa, registradas) if not veh else []

    base = {"placa": placa, "sugerencias": sugerencias}
    if placa_original != placa:
        base["corregida_desde"] = placa_original

    if veh and pasos.exists():
        ultimo = pasos.first()
        return {**base, "estado": ESTADO_CON_PASO,
                "vehiculo": {"propietario": veh.propietario, "categoria": veh.categoria,
                             "ejes": veh.ejes, "saldo": str(veh.saldo)},
                "total_pasos": pasos.count(),
                "ultimo_paso": serializar_paso(ultimo)}
    if veh:
        return {**base, "estado": ESTADO_SIN_PASO,
                "vehiculo": {"propietario": veh.propietario, "categoria": veh.categoria,
                             "ejes": veh.ejes, "saldo": str(veh.saldo)}}
    if pasos.exists():
        return {**base, "estado": ESTADO_NO_REGISTRADA, "total_pasos": pasos.count(),
                "ultimo_paso": serializar_paso(pasos.first())}
    return {**base, "estado": ESTADO_NO_EXISTE}


# --------------------------------------------------------------------------
# Registro de un paso (flujo principal de la caseta)
# --------------------------------------------------------------------------
def _guardar_evidencia(imagen_bytes):
    nombre = f"evidencias/{timezone.now():%Y/%m/%d}/{uuid.uuid4().hex}.jpg"
    ruta = default_storage.save(nombre, ContentFile(imagen_bytes))
    return f"{settings.PUBLIC_BASE_URL}{settings.MEDIA_URL}{ruta}"


def resumen_caseta(caseta_id):
    hoy = timezone.localtime().replace(hour=0, minute=0, second=0, microsecond=0)
    qs = Paso.objects.filter(caseta_id=caseta_id, created_at__gte=hoy)
    cobrados = qs.filter(estado=Paso.ESTADO_OK).aggregate(r=Sum("monto"))["r"] or Decimal("0")
    return {
        "caseta_id": caseta_id,
        "fecha": hoy.date().isoformat(),
        "pasos": qs.count(),
        "recaudacion": str(cobrados),
        "alertas": Alerta.objects.filter(paso__caseta_id=caseta_id, created_at__gte=hoy).count(),
    }


def registrar_frame(imagen_bytes, caseta, usuario):
    """Frame -> inferencia -> paso + alerta -> tiempo real. Devuelve dict para la app móvil."""
    inf = inferir(imagen_bytes)
    leida = inf["placa_leida"]
    placa = placas.corregir_ocr(placas.normalizar(leida))

    if not placas.es_valida(placa) or inf["confianza"] < settings.OCR_CONFIANZA_MIN:
        return {"detectado": False, "motivo": "placa_ilegible", "inferencia": inf}

    # Anti-duplicados: mismo vehículo, misma caseta, dentro de la ventana
    desde = timezone.now() - timedelta(seconds=settings.DEDUP_SEGUNDOS)
    reciente = Paso.objects.filter(caseta=caseta, placa_normalizada=placa, created_at__gte=desde).first()
    if reciente:
        return {"detectado": True, "duplicado": True, "paso": serializar_paso(reciente), "inferencia": inf}

    veh = Vehiculo.objects.filter(placa=placa, activo=True).first()
    categoria = inf["categoria"] or (veh.categoria if veh else "")
    ejes = inf["ejes"] or (veh.ejes if veh else 0)
    monto = calcular_tarifa(categoria, ejes) if categoria else Decimal("0")

    alerta_tipo = None
    if veh is None:
        estado, alerta_tipo = Paso.ESTADO_NO_REGISTRADA, Alerta.TIPO_NO_REGISTRADA
    elif veh.saldo < monto:
        estado, alerta_tipo = Paso.ESTADO_SIN_SALDO, Alerta.TIPO_SIN_SALDO
    else:
        estado = Paso.ESTADO_OK
        veh.saldo -= monto
        veh.save(update_fields=["saldo"])

    paso = Paso.objects.create(
        placa_leida=leida, placa_normalizada=placa, confianza_ocr=inf["confianza"],
        categoria_detectada=categoria, ejes_detectados=ejes,
        monto=monto if estado == Paso.ESTADO_OK else Decimal("0"),
        caseta=caseta, usuario=usuario, estado=estado, latencia_ms=inf["latencia_total_ms"],
        imagen_url=_guardar_evidencia(imagen_bytes),
    )
    data_paso = serializar_paso(paso)
    emitir("paso.nuevo", data_paso)

    if alerta_tipo:
        al = Alerta.objects.create(paso=paso, tipo=alerta_tipo)
        emitir("alerta.nueva", {"id": al.id, "tipo": al.tipo, "atendida": False,
                                "created_at": timezone.localtime(al.created_at).isoformat(),
                                "paso": data_paso})
    emitir("resumen.actualizado", resumen_caseta(caseta.id))

    return {"detectado": True, "duplicado": False, "paso": data_paso, "tarifa": str(monto), "inferencia": inf}
