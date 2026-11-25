# Inferencia (M1 + M2 + M3 en un solo endpoint)

| Modelo | Qué hace | De dónde sale |
|---|---|---|
| M1 | Detecta la placa (YOLOv9-t ONNX) y la lee (fast-plate-ocr o EasyOCR); normaliza a `2481KLM` | `modelo/` (proyecto del docente, sin entrenar) |
| M2 | Segmenta el vehículo → `moto/auto/minibus/camion/bus` | `modelos/m2_vehiculos.pt` (entrenado); si no existe usa YOLOE sin entrenar |
| M3 | Llantas con keypoints → número de ejes | `modelos/m3_llantas.pt` (entrenado); si no existe usa YOLOE + geometría |

`GET /health` · `POST /predict` (campo `file`, cabecera `X-API-Key`, `?anotada=true` devuelve la imagen dibujada).

## Levantarlo en Colab
Abrir `colab_servidor.ipynb`, subir `inferencia.zip` y ejecutar las celdas. Imprime la línea `INFERENCE_URL=...`
que se pega en el `.env` del servidor web (`sudo systemctl restart peaje`).
Los pesos propios (`.pt`) se guardan en Google Drive (`MyDrive/peaje/`), no en el repositorio.

## Pruebas y métricas
```bash
python -m unittest discover -s tests -v                 # lógica de ejes, placas y API
python evaluar_ocr.py fotos/ etiquetas.csv fastplate easyocr   # precisión del OCR para el informe
python diagnostico.py | tee diagnostico_colab.txt        # evidencia del entorno (punto extra)
```
