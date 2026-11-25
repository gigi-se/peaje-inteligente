"""M3: llantas con keypoints -> número de ejes."""
import cv2
import numpy as np

import config
from ejes_logic import contar_ejes

PROMPTS_LLANTA = ["wheel", "tire", "car wheel"]


def _iou(a, b):
    x1, y1, x2, y2 = max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3])
    inter = max(0, x2 - x1) * max(0, y2 - y1)
    ua = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / ua if ua > 0 else 0


def nms(items, umbral=0.5):
    res = []
    for d in sorted(items, key=lambda d: -d["conf"]):
        if all(_iou(d["box"], r["box"]) < umbral for r in res):
            res.append(d)
    return res


def kps_de_mascara(mask):
    """5 keypoints desde el contorno: centro (elipse ajustada), contacto, superior, izquierda, derecha."""
    cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    if not cnts:
        return None
    c = max(cnts, key=cv2.contourArea)
    if cv2.contourArea(c) < 8:
        return None
    pts = c.reshape(-1, 2).astype(float)
    (cx, cy), _, _ = cv2.fitEllipse(c) if len(pts) >= 5 else ((*pts.mean(0),), 0, 0)
    k = np.array([[cx, cy], pts[pts[:, 1].argmax()], pts[pts[:, 1].argmin()], pts[pts[:, 0].argmin()], pts[pts[:, 0].argmax()]])
    return np.concatenate([k, np.ones((5, 1))], axis=1)


def kps_desde_caja(box, centro=None, conf=1.0):
    """Si el modelo tiene 1 solo keypoint (centro de la rueda), se completan los 5 usando la caja."""
    x1, y1, x2, y2 = box
    cx, cy = centro if centro is not None else ((x1 + x2) / 2, (y1 + y2) / 2)
    return np.array([[cx, cy, conf], [cx, y2, conf], [cx, y1, conf], [x1, cy, conf], [x2, cy, conf]], dtype=float)


class M3:
    def __init__(self):
        from ultralytics import YOLO, YOLOE
        import torch
        self.dev = 0 if torch.cuda.is_available() else "cpu"
        if config.M3_PESOS.exists():
            self.modelo, self.zero_shot, self.nombre = YOLO(str(config.M3_PESOS)), False, "propio (YOLO-pose entrenado)"
        else:
            self.modelo = YOLOE(config.YOLOE_PESOS)
            self.modelo.set_classes(PROMPTS_LLANTA, self.modelo.get_text_pe(PROMPTS_LLANTA))
            self.zero_shot, self.nombre = True, "YOLOE + geometría sin entrenar (reemplazar por M3 propio)"

    def llantas(self, img_bgr):
        if self.zero_shot:
            r = self.modelo.predict(img_bgr, conf=config.CONF_LLANTA, imgsz=config.IMGSZ, device=self.dev, verbose=False)[0]
            H, W = r.orig_shape
            out = []
            if r.masks is not None:
                for poly, s, b in zip(r.masks.xy, r.boxes.conf.cpu().numpy(), r.boxes.xyxy.cpu().numpy()):
                    if len(poly) < 3:
                        continue
                    m = np.zeros((H, W), np.uint8)
                    cv2.fillPoly(m, [poly.astype(np.int32)], 1)
                    k = kps_de_mascara(m)
                    if k is not None:
                        k[:, 2] = s
                        out.append({"conf": float(s), "box": b.tolist(), "kps": k})
            return nms(out, 0.5)
        r = self.modelo.predict(img_bgr, conf=config.CONF_LLANTA, imgsz=640, device=self.dev, verbose=False)[0]
        out = []
        if r.keypoints is not None and len(r.boxes):
            xy = r.keypoints.xy.cpu().numpy()
            kc = r.keypoints.conf.cpu().numpy() if r.keypoints.conf is not None else np.ones(xy.shape[:2])
            for b, s, p, c in zip(r.boxes.xyxy.cpu().numpy(), r.boxes.conf.cpu().numpy(), xy, kc):
                if len(p) >= 5:
                    k = np.concatenate([p[:5], c[:5, None]], 1)
                else:   # modelo de 1 keypoint por rueda
                    k = kps_desde_caja(b.tolist(), tuple(p[0]) if len(p) else None, float(c[0]) if len(c) else 1.0)
                out.append({"conf": float(s), "box": b.tolist(), "kps": k})
        return out

    def ejes(self, img_bgr, vbox):
        return contar_ejes(vbox, self.llantas(img_bgr))
