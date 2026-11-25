"""M1: detección de placas (YOLOv9-t ONNX del docente) + OCR + normalización boliviana."""
import re
import time

import cv2
import numpy as np
import onnxruntime as ort

import config

LADO = 384
FORMATO = re.compile(r"^\d{3,4}[A-Z]{3}$")
A_LETRA = {"0": "O", "1": "I", "8": "B", "5": "S", "2": "Z", "6": "G"}
A_DIGITO = {v: k for k, v in A_LETRA.items()}


def limpiar(texto):
    return re.sub(r"[^A-Z0-9]", "", (texto or "").upper())


def _corregir(ventana, n_dig):
    """Los últimos 3 caracteres son letras y los anteriores dígitos (corrige confusiones de OCR)."""
    cabeza = "".join(A_DIGITO.get(c, c) if not c.isdigit() else c for c in ventana[:n_dig])
    cola = "".join(A_LETRA.get(c, c) if c.isdigit() else c for c in ventana[n_dig:])
    return cabeza + cola


def extraer_placa(texto):
    """Busca dentro del texto crudo (que puede incluir 'BOLIVIA' u otros) la placa 4 dígitos + 3 letras
    (o 3 + 3). Devuelve (placa, n_correcciones) o ("", 0). Prefiere el formato de 7 caracteres."""
    t = limpiar(texto)
    mejor = None
    for largo in (7, 6):
        for i in range(len(t) - largo + 1):
            crudo = t[i:i + largo]
            fijo = _corregir(crudo, largo - 3)
            if FORMATO.match(fijo):
                cambios = sum(a != b for a, b in zip(crudo, fijo))
                if mejor is None or cambios < mejor[1]:
                    mejor = (fijo, cambios)
        if mejor:
            return mejor
    return "", 0


class Detector:
    """Detector de placas ONNX (misma preparación y salida que el proyecto del docente)."""

    def __init__(self, ruta=None):
        proveedores = [p for p in ("CUDAExecutionProvider", "CPUExecutionProvider") if p in ort.get_available_providers()]
        self.sesion = ort.InferenceSession(str(ruta or config.DETECTOR_ONNX), providers=proveedores)
        self.entrada = self.sesion.get_inputs()[0].name

    def detectar(self, imagen, umbral=None):
        umbral = config.UMBRAL_PLACA if umbral is None else umbral
        alto, ancho = imagen.shape[:2]
        escala = min(LADO / alto, LADO / ancho)
        nw, nh = round(ancho * escala), round(alto * escala)
        mx, my = (LADO - nw) / 2, (LADO - nh) / 2
        lienzo = cv2.resize(imagen, (nw, nh), interpolation=cv2.INTER_LINEAR)
        lienzo = cv2.copyMakeBorder(lienzo, round(my - 0.1), round(my + 0.1), round(mx - 0.1), round(mx + 0.1),
                                    cv2.BORDER_CONSTANT, value=(114, 114, 114))
        x = (lienzo[:, :, ::-1].transpose(2, 0, 1) / 255.0).astype(np.float32)[None]
        salida = self.sesion.run(None, {self.entrada: x})[0]
        cajas = []
        for _, x1, y1, x2, y2, _, conf in salida:
            if conf < umbral:
                continue
            x1, x2 = [(v - mx) / escala for v in (x1, x2)]
            y1, y2 = [(v - my) / escala for v in (y1, y2)]
            cajas.append((int(max(0, x1)), int(max(0, y1)), int(min(ancho, x2)), int(min(alto, y2)), float(conf)))
        return cajas


class OcrFastPlate:
    nombre = "fast-plate-ocr"

    def __init__(self):
        from fast_plate_ocr import LicensePlateRecognizer
        self.lector = LicensePlateRecognizer(onnx_model_path=config.OCR_ONNX, plate_config_path=config.OCR_YAML)

    def leer(self, recorte_bgr):
        p = self.lector.run_one(cv2.cvtColor(recorte_bgr, cv2.COLOR_BGR2RGB), return_confidence=True)
        conf = float(np.asarray(p.char_probs).mean()) if p.char_probs is not None else 0.0
        return p.plate, conf


class OcrEasy:
    nombre = "EasyOCR"
    PERMITIDOS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"

    def __init__(self):
        import easyocr
        import torch
        self.lector = easyocr.Reader(["en"], gpu=torch.cuda.is_available(), verbose=False)

    def leer(self, recorte_bgr):
        lecturas = self.lector.readtext(recorte_bgr, allowlist=self.PERMITIDOS)
        if lecturas:   # solo el texto más alto: los caracteres de la placa, no las leyendas pequeñas
            alt = lambda l: max(p[1] for p in l[0]) - min(p[1] for p in l[0])
            mx = max(alt(l) for l in lecturas)
            lecturas = [l for l in lecturas if alt(l) >= mx * 0.6]
        lecturas.sort(key=lambda l: l[0][0][0])
        texto = "".join(t for _, t, _ in lecturas)
        conf = sum(c for _, _, c in lecturas) / len(lecturas) if lecturas else 0.0
        return texto, float(conf)


def crear_ocr(motor=None):
    return {"fastplate": OcrFastPlate, "easyocr": OcrEasy}[motor or config.OCR_ENGINE]()


class M1:
    def __init__(self, motor=None):
        self.detector = Detector()
        self.ocr = crear_ocr(motor)

    def leer(self, imagen):
        """Devuelve la mejor placa de la imagen: {texto, confianza, bbox, crudo, valida}."""
        t0 = time.perf_counter()
        candidatas = []
        for x1, y1, x2, y2, cdet in self.detector.detectar(imagen):
            if x2 - x1 < 8 or y2 - y1 < 8:
                continue
            crudo, clectura = self.ocr.leer(imagen[y1:y2, x1:x2])
            placa, cambios = extraer_placa(crudo)
            # confianza final: lectura del OCR (penalizada si hubo correcciones) combinada con la detección
            conf = clectura * (0.9 ** cambios) * (0.5 + 0.5 * cdet) if placa else 0.0
            candidatas.append({"texto": placa or limpiar(crudo), "crudo": limpiar(crudo), "valida": bool(placa),
                               "confianza": round(float(conf), 3), "bbox": [x1, y1, x2, y2],
                               "confianza_deteccion": round(cdet, 3)})
        candidatas.sort(key=lambda c: (c["valida"], c["confianza"]), reverse=True)
        res = candidatas[0] if candidatas else {"texto": "", "crudo": "", "valida": False, "confianza": 0.0,
                                                "bbox": None, "confianza_deteccion": 0.0}
        res["ms"] = round((time.perf_counter() - t0) * 1000, 1)
        return res
