"""Conteo de ejes a partir de llantas con 5 keypoints (centro, contacto, superior, izquierda, derecha).
Lógica del notebook del docente (celda 6), aislada y sin dependencias de modelos para poder probarla.

Cada llanta: {'conf': float, 'box': [x1,y1,x2,y2], 'kps': np.ndarray (5,3)}
"""
import numpy as np

UMBRAL_CONTENCION = 0.7   # una detección contenida en otra (p. ej. el aro dentro de la llanta) se descarta
UMBRAL_CERCANA = 0.65     # altura visible mínima (respecto a la mayor) para ser llanta del lado cercano
SEPARACION_EJE = 0.6      # distancia mínima en x entre ejes, en diámetros (ruedas dobles = un solo eje)


def altura_visible(l):
    return max(1.0, l["kps"][1, 1] - l["kps"][2, 1])          # contacto.y - superior.y


def _contenida(a, b):
    x1, y1, x2, y2 = max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3])
    inter = max(0, x2 - x1) * max(0, y2 - y1)
    return inter / max(1e-6, (a[2] - a[0]) * (a[3] - a[1]))


def limpiar_llantas(llantas):
    orden = sorted(llantas, key=lambda l: -(l["box"][2] - l["box"][0]) * (l["box"][3] - l["box"][1]))
    res = []
    for l in orden:
        if all(_contenida(l["box"], r["box"]) < UMBRAL_CONTENCION for r in res):
            res.append(l)
    return res


def llantas_de_vehiculo(vbox, llantas):
    """Llantas cuyo centro está dentro del vehículo y en su parte baja."""
    x1, y1, x2, y2 = vbox
    w, h = x2 - x1, y2 - y1
    out = []
    for l in llantas:
        cx, cy = l["kps"][0, :2]
        if x1 - 0.05 * w <= cx <= x2 + 0.05 * w and y1 + 0.35 * h <= cy <= y2 + 0.10 * h:
            out.append(l)
    return out


def analizar_ejes(vbox, ls):
    """Devuelve dict(ejes, vista, nota, llantas). ejes=None si no es determinable (vista frontal/posterior)."""
    if not ls:
        return {"ejes": None, "vista": "-", "nota": "Sin llantas detectadas", "llantas": []}
    hmax = max(altura_visible(l) for l in ls)
    cercanas = [l for l in ls if altura_visible(l) >= UMBRAL_CERCANA * hmax]
    x1, y1, x2, y2 = vbox
    proporcion = (x2 - x1) / max(1.0, y2 - y1)
    if len(cercanas) == 2 and proporcion < 1.6:        # 2 elipses angostas a la misma altura y caja poco alargada
        a, b = cercanas
        angostas = all((l["kps"][4, 0] - l["kps"][3, 0]) / altura_visible(l) < 0.65 for l in cercanas)
        misma_altura = abs(a["kps"][1, 1] - b["kps"][1, 1]) < 0.15 * hmax
        if angostas and misma_altura:
            return {"ejes": None, "vista": "frontal/posterior", "nota": "No determinable en esta vista", "llantas": cercanas}
    xs = sorted(l["kps"][0, 0] for l in cercanas)
    diam = float(np.median([altura_visible(l) for l in cercanas]))
    ejes = 1 + sum(1 for p, q in zip(xs, xs[1:]) if q - p > SEPARACION_EJE * diam)
    redondez = np.median([(l["kps"][4, 0] - l["kps"][3, 0]) / altura_visible(l) for l in cercanas])
    vista = "lateral" if redondez > 0.8 else "3/4"
    nota = ""
    if ejes < 2:
        ejes, nota = 2, "Mínimo asumido (solo se detectó 1 eje)"
    return {"ejes": int(ejes), "vista": vista, "nota": nota, "llantas": cercanas}


def contar_ejes(vbox, llantas):
    return analizar_ejes(vbox, llantas_de_vehiculo(vbox, limpiar_llantas(llantas)))
