"""Diagnóstico del entorno (Python, torch, CUDA, ultralytics, ONNX, OCR). Ejecutar en cada entorno de la nube
y guardar la salida en la carpeta de evidencias:   python diagnostico.py | tee diagnostico_colab.txt"""
import importlib
import platform
import sys

print("Python:", sys.version.split()[0], "|", platform.platform())
for modulo, etiqueta in [("torch", "torch"), ("torchvision", "torchvision"), ("ultralytics", "ultralytics"),
                         ("onnxruntime", "onnxruntime"), ("fast_plate_ocr", "fast-plate-ocr"), ("easyocr", "easyocr"),
                         ("cv2", "opencv"), ("numpy", "numpy"), ("fastapi", "fastapi"), ("uvicorn", "uvicorn")]:
    try:
        m = importlib.import_module(modulo)
        print(f"{etiqueta}:", getattr(m, "__version__", "instalado"))
    except Exception as e:
        print(f"{etiqueta}: NO DISPONIBLE ({type(e).__name__})")
try:
    import torch
    print("CUDA disponible:", torch.cuda.is_available(), "| CUDA build:", torch.version.cuda)
    if torch.cuda.is_available():
        print("GPU:", torch.cuda.get_device_name(0))
except Exception:
    pass
