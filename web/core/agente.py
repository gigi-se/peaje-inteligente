"""Agente conversacional (versión base, sin LLM).

Responde SOLO con datos de la BD (core.services.estado_de_placa). En la siguiente
fase se le añade un LLM con function calling que usa estas mismas funciones como
tools; esta versión determinista queda como respaldo si el LLM no responde.
"""
import re

from django.conf import settings

from . import agente_llm, placas, services


def _extraer_placa(mensaje):
    """Busca algo con forma de placa en el texto (admite '2481-KLM', '2481 klm', ...)."""
    texto = (mensaje or "").upper()
    # Une un grupo de dígitos seguido de letras separados por guion/espacio
    for m in re.finditer(r"[0-9OIBSZG]{3,4}[\s\-]*[A-Z0-9]{3}", texto):
        cand = placas.normalizar(m.group())
        if placas.es_valida(placas.corregir_ocr(cand)):
            return cand
    for token in re.findall(r"[A-Z0-9\-]{5,9}", texto):
        cand = placas.normalizar(token)
        if 6 <= len(cand) <= 7:
            return cand
    return ""


def _texto(r):
    e = r["estado"]
    pl = r["placa"]
    pref = f"Interpreté la placa como **{pl}** (leí «{r['corregida_desde']}»). " if r.get("corregida_desde") else ""
    sug = ""
    if r.get("sugerencias"):
        sug = " ¿Quisiste decir " + " o ".join(f"**{s}**" for s in r["sugerencias"]) + "?"

    if e == "formato_invalido":
        return f"{r['mensaje']} Envíame la placa o una foto más clara."
    if e == services.ESTADO_CON_PASO:
        p = r["ultimo_paso"]
        return (f"{pref}La placa **{pl}** está registrada ({r['vehiculo']['propietario']}) y tiene "
                f"{r['total_pasos']} paso(s). Último: {p['created_at'][:16].replace('T', ' ')} en "
                f"{p['caseta']}, categoría {p['categoria'] or '—'}, monto Bs {p['monto']}.")
    if e == services.ESTADO_SIN_PASO:
        return f"{pref}La placa **{pl}** está registrada a nombre de {r['vehiculo']['propietario']}, pero nunca pasó por el peaje."
    if e == services.ESTADO_NO_REGISTRADA:
        p = r["ultimo_paso"]
        return (f"{pref}La placa **{pl}** fue identificada por la cámara ({r['total_pasos']} vez/veces, último en "
                f"{p['caseta']}) pero **no está registrada**: posible evasión.{sug}")
    return f"{pref}No existe ningún registro de la placa **{pl}**.{sug}"


def responder(mensaje="", imagen_bytes=None):
    """Devuelve {"respuesta": str, "estado": ..., "datos": {...}} o pide otra imagen."""
    origen = "texto"
    placa = ""
    if imagen_bytes:
        origen = "imagen"
        try:
            inf = services.inferir(imagen_bytes)
        except services.InferenciaError as e:
            return {"respuesta": f"No pude analizar la imagen: {e}", "estado": "error_inferencia"}
        placa = placas.corregir_ocr(placas.normalizar(inf["placa_leida"]))
        if not placas.es_valida(placa) or inf["confianza"] < settings.OCR_CONFIANZA_MIN:
            return {"respuesta": "No pude leer una placa legible en la imagen. ¿Puedes enviar otra foto más cercana y con buena luz?",
                    "estado": "imagen_ilegible"}
    else:
        placa = _extraer_placa(mensaje)
        if not placa:
            return {"respuesta": "Envíame una placa (por ejemplo 2481KLM) o una foto de la placa y te digo su estado en el sistema.",
                    "estado": "sin_placa"}

    r = services.estado_de_placa(placa)
    out = {"respuesta": _texto(r), "estado": r["estado"], "origen": origen, "datos": r, "motor": "reglas"}
    if agente_llm.disponible():
        try:
            consulta = mensaje if origen == "texto" else f"{mensaje or 'Consulta'} (placa leída de una foto: {placa})"
            res = agente_llm.responder(consulta)
            if res["texto"]:
                out.update(respuesta=res["texto"], motor="llm", herramientas=res["herramientas"])
        except Exception:
            pass   # respaldo: respuesta determinista
    return out
