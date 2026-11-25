"""Configuración del endpoint de inferencia (todo por variables de entorno)."""
import os
from pathlib import Path

BASE = Path(__file__).resolve().parent


def _ruta(nombre, defecto):
    p = Path(os.environ.get(nombre, defecto))
    return p if p.is_absolute() else BASE / p


API_KEY = os.environ.get("INFERENCE_API_KEY", "")            # si está vacía, no se exige
OCR_ENGINE = os.environ.get("OCR_ENGINE", "fastplate")       # fastplate | easyocr
UMBRAL_PLACA = float(os.environ.get("UMBRAL_PLACA", "0.40"))
CONF_VEHICULO = float(os.environ.get("CONF_VEHICULO", "0.30"))
CONF_LLANTA = float(os.environ.get("CONF_LLANTA", "0.15"))
IMGSZ = int(os.environ.get("IMGSZ", "1024"))

DETECTOR_ONNX = _ruta("M1_DETECTOR", "modelo/yolo-v9-t-384-license-plates-end2end.onnx")
OCR_ONNX = _ruta("M1_OCR_ONNX", "modelo/cct_xs_v2_global.onnx")
OCR_YAML = _ruta("M1_OCR_YAML", "modelo/cct_xs_v2_global_plate_config.yaml")

# Pesos propios entrenados en Roboflow/Colab. Si NO existen se usa un método sin entrenamiento (YOLOE).
M2_PESOS = _ruta("M2_WEIGHTS", "modelos/m2_vehiculos.pt")
M3_PESOS = _ruta("M3_WEIGHTS", "modelos/m3_llantas.pt")
YOLOE_PESOS = os.environ.get("YOLOE_WEIGHTS", "yoloe-11l-seg.pt")
