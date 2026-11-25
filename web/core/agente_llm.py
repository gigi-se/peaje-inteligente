"""Agente con LLM (API compatible con OpenAI: Qwen vía vLLM/Ollama/OpenRouter, etc.) y function calling.

El modelo NO inventa datos: solo puede consultar la BD a través de dos herramientas
(consultar_placa, historial_placa). Si el LLM no está configurado o falla, el llamador usa el agente determinista.
"""
import json

import requests
from django.conf import settings

from . import placas, services
from .models import Ajuste, Paso

SISTEMA = (
    "Eres el asistente de un sistema de control de peaje en Bolivia. Respondes en español, breve y claro. "
    "Para cualquier dato de una placa DEBES usar las herramientas; nunca inventes propietarios, montos ni fechas. "
    "Estados posibles de una placa: (1) registrada con pasos, (2) registrada sin pasos, (3) no registrada pero "
    "detectada por cámara (posible evasión), (4) sin ningún registro. Si el usuario no da una placa, pídela."
)

TOOLS = [
    {"type": "function", "function": {
        "name": "consultar_placa",
        "description": "Estado de una placa en el sistema: registrada o no, propietario, total de pasos y último paso.",
        "parameters": {"type": "object", "properties": {"placa": {"type": "string", "description": "Ej. 2481KLM"}},
                       "required": ["placa"]}}},
    {"type": "function", "function": {
        "name": "historial_placa",
        "description": "Últimos pasos por el peaje de una placa (fecha, caseta, categoría, ejes, monto).",
        "parameters": {"type": "object", "properties": {"placa": {"type": "string"},
                                                        "limite": {"type": "integer", "default": 5}},
                       "required": ["placa"]}}},
]


def config():
    def a(clave, defecto):
        x = Ajuste.objects.filter(clave=clave).first()
        return x.valor if x and x.valor != "" else defecto
    return {"url": a("llm_base_url", settings.LLM_BASE_URL).rstrip("/"),
            "modelo": a("llm_model", settings.LLM_MODEL),
            "clave": a("llm_api_key", settings.LLM_API_KEY)}


def disponible():
    return bool(config()["url"])


def _ejecutar(nombre, args):
    placa = placas.normalizar(args.get("placa", ""))
    if nombre == "consultar_placa":
        return services.estado_de_placa(placa)
    if nombre == "historial_placa":
        qs = Paso.objects.filter(placa_normalizada=placa).select_related("caseta")[:max(1, min(int(args.get("limite", 5)), 20))]
        return {"placa": placa, "pasos": [{"fecha": p.created_at.isoformat()[:16], "caseta": p.caseta.nombre,
                                           "categoria": p.categoria, "ejes": p.ejes, "monto": str(p.monto),
                                           "estado": p.estado} for p in qs]}
    return {"error": f"herramienta desconocida: {nombre}"}


def _llamar(cfg, mensajes):
    headers = {"Content-Type": "application/json"}
    if cfg["clave"]:
        headers["Authorization"] = f"Bearer {cfg['clave']}"
    r = requests.post(f"{cfg['url']}/chat/completions", headers=headers, timeout=60,
                      json={"model": cfg["modelo"], "messages": mensajes, "tools": TOOLS, "temperature": 0.2})
    r.raise_for_status()
    return r.json()["choices"][0]["message"]


def responder(mensaje, max_vueltas=4):
    """Devuelve el texto del LLM tras ejecutar sus herramientas. Lanza excepción si algo falla."""
    cfg = config()
    msgs = [{"role": "system", "content": SISTEMA}, {"role": "user", "content": mensaje}]
    usadas = []
    for _ in range(max_vueltas):
        m = _llamar(cfg, msgs)
        llamadas = m.get("tool_calls") or []
        if not llamadas:
            return {"texto": (m.get("content") or "").strip(), "herramientas": usadas}
        msgs.append({"role": "assistant", "content": m.get("content") or "", "tool_calls": llamadas})
        for c in llamadas:
            try:
                args = json.loads(c["function"].get("arguments") or "{}")
            except ValueError:
                args = {}
            res = _ejecutar(c["function"]["name"], args)
            usadas.append(c["function"]["name"])
            msgs.append({"role": "tool", "tool_call_id": c["id"], "content": json.dumps(res, ensure_ascii=False, default=str)})
    raise RuntimeError("El LLM no terminó de responder.")
