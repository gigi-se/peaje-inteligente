"""Endpoint único de inferencia: M1 (placa + OCR) + M2 (categoría) + M3 (ejes).

    uvicorn app:app --host 0.0.0.0 --port 8000

POST /predict  (multipart, campo "file" = imagen JPEG/PNG; cabecera X-API-Key si INFERENCE_API_KEY está definida)
  -> {"placa": {"texto","confianza","bbox","valida"}, "vehiculo": {"categoria","confianza","area_mascara"},
      "ejes": 3, "keypoints": [[x,y,conf],...], "latencia_ms": 412.3, "tiempos_ms": {...}}
GET /health    -> estado y modelos cargados
"""
import base64
import threading
import time

import cv2
import numpy as np
from fastapi import FastAPI, File, Header, HTTPException, UploadFile
from starlette.concurrency import run_in_threadpool

import config
from m2_vehiculos import elegir_vehiculo

app = FastAPI(title="Inferencia del peaje (M1 + M2 + M3)", version="1.0.0")
_lock = threading.Lock()          # una inferencia a la vez sobre la GPU
_modelos = {}


def cargar_modelos():
    """Carga perezosa (la primera petición tarda más). Se puede reemplazar en las pruebas."""
    if not _modelos:
        from m1_placas import M1
        from m2_vehiculos import M2
        from m3_ejes import M3
        _modelos.update(m1=M1(), m2=M2(), m3=M3())
    return _modelos


def anotar(img, placa, veh, llantas):
    out = img.copy()
    if placa.get("bbox"):
        x1, y1, x2, y2 = placa["bbox"]
        cv2.rectangle(out, (x1, y1), (x2, y2), (0, 200, 0), 3)
        cv2.putText(out, placa["texto"] or "?", (x1, max(25, y1 - 8)), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 200, 0), 2)
    if veh:
        x1, y1, x2, y2 = map(int, veh["box"])
        cv2.rectangle(out, (x1, y1), (x2, y2), (219, 152, 52), 3)
        cv2.putText(out, veh["categoria"], (x1, max(25, y1 - 8)), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (219, 152, 52), 2)
    for k in llantas:
        cv2.circle(out, (int(k[0]), int(k[1])), 9, (60, 60, 250), -1)
    return "data:image/jpeg;base64," + base64.b64encode(cv2.imencode(".jpg", out, [cv2.IMWRITE_JPEG_QUALITY, 80])[1]).decode()


def analizar(img, con_imagen=False):
    m = cargar_modelos()
    t0 = time.perf_counter()
    placa = m["m1"].leer(img)
    t1 = time.perf_counter()
    vehiculos = m["m2"].segmentar(img)
    veh = elegir_vehiculo(vehiculos, placa.get("bbox"))
    t2 = time.perf_counter()
    h, w = img.shape[:2]
    res_ejes = m["m3"].ejes(img, veh["box"] if veh else [0, 0, w, h])
    t3 = time.perf_counter()

    kps = [[round(float(l["kps"][0, 0]), 1), round(float(l["kps"][0, 1]), 1), round(float(l["conf"]), 3)]
           for l in res_ejes["llantas"]]
    out = {
        "placa": {"texto": placa["texto"] if placa["valida"] else "", "confianza": placa["confianza"],
                  "bbox": placa["bbox"], "valida": placa["valida"], "crudo": placa["crudo"]},
        "vehiculo": {"categoria": veh["categoria"] if veh else "", "confianza": round(veh["conf"], 3) if veh else 0.0,
                     "area_mascara": round(veh["area"], 3) if veh else 0.0},
        "ejes": res_ejes["ejes"], "vista": res_ejes["vista"], "nota_ejes": res_ejes["nota"],
        "keypoints": kps,
        "latencia_ms": round((t3 - t0) * 1000, 1),
        "tiempos_ms": {"m1": round((t1 - t0) * 1000, 1), "m2": round((t2 - t1) * 1000, 1), "m3": round((t3 - t2) * 1000, 1)},
    }
    if con_imagen:
        out["imagen_anotada"] = anotar(img, placa, veh, [k for k in kps])
    return out


def _auth(clave):
    if config.API_KEY and clave != config.API_KEY:
        raise HTTPException(status_code=401, detail="API key inválida")


@app.get("/health")
def health(x_api_key: str = Header(default="")):
    _auth(x_api_key)
    info = {"ok": True, "ocr": config.OCR_ENGINE, "m2_propio": config.M2_PESOS.exists(),
            "m3_propio": config.M3_PESOS.exists(), "cargados": list(_modelos)}
    try:
        import torch
        info["gpu"] = torch.cuda.get_device_name(0) if torch.cuda.is_available() else None
    except Exception:
        info["gpu"] = None
    return info


@app.post("/predict")
async def predict(file: UploadFile = File(...), anotada: bool = False, x_api_key: str = Header(default="")):
    _auth(x_api_key)
    datos = await file.read()
    img = cv2.imdecode(np.frombuffer(datos, np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        raise HTTPException(status_code=400, detail="No se pudo decodificar la imagen")

    def trabajo():
        with _lock:
            return analizar(img, anotada)
    return await run_in_threadpool(trabajo)
