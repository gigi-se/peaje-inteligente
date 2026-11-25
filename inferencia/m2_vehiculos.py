"""M2: segmentación de instancias del vehículo -> categoría (moto, auto, minibus, microbus, camion, bus)."""
import cv2
import numpy as np

import config

NORMALIZAR = {"auto": "auto", "car": "auto", "auto particular": "auto", "automovil": "auto", "vagoneta": "auto",
              "sedan": "auto", "suv": "auto", "moto": "moto", "motorcycle": "moto", "motorbike": "moto",
              "bus": "bus", "minibus": "minibus", "minibús": "minibus", "microbus": "microbus", "micro": "microbus", "microbús": "microbus", "van": "minibus",
              "camion": "camion", "camión": "camion", "truck": "camion", "cargo truck": "camion"}
# Prompts de texto del método sin entrenamiento (YOLOE) -> categoría
PROMPTS = {"car": "auto", "sedan": "auto", "suv": "auto", "motorcycle": "moto", "bus": "bus",
           "minibus": "minibus", "van": "minibus", "truck": "camion", "cargo truck": "camion"}


def elegir_vehiculo(vehiculos, bbox_placa=None):
    """Vehículo principal: el que contiene el centro de la placa (el más pequeño si hay varios);
    si no hay placa, el de mayor área de máscara."""
    if not vehiculos:
        return None
    if bbox_placa:
        cx, cy = (bbox_placa[0] + bbox_placa[2]) / 2, (bbox_placa[1] + bbox_placa[3]) / 2
        dentro = [v for v in vehiculos if v["box"][0] <= cx <= v["box"][2] and v["box"][1] <= cy <= v["box"][3]]
        if dentro:
            return min(dentro, key=lambda v: (v["box"][2] - v["box"][0]) * (v["box"][3] - v["box"][1]))
    return max(vehiculos, key=lambda v: v["area"])


class M2:
    def __init__(self):
        from ultralytics import YOLO, YOLOE
        import torch
        self.dev = 0 if torch.cuda.is_available() else "cpu"
        if config.M2_PESOS.exists():
            self.modelo, self.mapa, self.nombre = YOLO(str(config.M2_PESOS)), NORMALIZAR, "propio (YOLO-seg entrenado)"
        else:   # método sin entrenamiento: vocabulario abierto
            nombres = list(PROMPTS)
            self.modelo = YOLOE(config.YOLOE_PESOS)
            self.modelo.set_classes(nombres, self.modelo.get_text_pe(nombres))
            self.mapa, self.nombre = PROMPTS, "YOLOE sin entrenar (reemplazar por M2 propio)"

    def segmentar(self, img_bgr):
        r = self.modelo.predict(img_bgr, conf=config.CONF_VEHICULO, device=self.dev, agnostic_nms=True, verbose=False)[0]
        H, W = r.orig_shape
        out = []
        if r.masks is None:
            return out
        for poly, c, s, b in zip(r.masks.xy, r.boxes.cls.cpu().numpy().astype(int),
                                 r.boxes.conf.cpu().numpy(), r.boxes.xyxy.cpu().numpy()):
            cat = self.mapa.get(str(r.names[c]).strip().lower())
            if cat is None or len(poly) < 3:
                continue
            out.append({"categoria": cat, "conf": float(s), "box": [float(v) for v in b],
                        "area": float(cv2.contourArea(poly.astype(np.float32)) / (H * W)),
                        "poligono": poly.astype(np.float32)})
        return out
