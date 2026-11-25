"""Normalización y validación de placas bolivianas + sugerencias ante errores de OCR.

Formatos válidos tras normalizar:
  - Actual:   4 dígitos + 3 letras  (2481KLM)
  - Antiguo:  3 dígitos + 3 letras  (123ABC)
"""
import re

PLACA_RE = re.compile(r"^\d{3,4}[A-Z]{3}$")

# Confusiones típicas del OCR
A_LETRA = {"0": "O", "1": "I", "8": "B", "5": "S", "2": "Z", "6": "G"}
A_DIGITO = {v: k for k, v in A_LETRA.items()}


def normalizar(texto):
    """Mayúsculas, sin guiones, espacios ni símbolos."""
    return re.sub(r"[^A-Z0-9]", "", (texto or "").upper())


def es_valida(placa):
    return bool(PLACA_RE.match(placa))


def corregir_ocr(placa):
    """Corrige por posición: los últimos 3 caracteres son letras, el resto dígitos."""
    if len(placa) not in (6, 7):
        return placa
    n_dig = len(placa) - 3
    cabeza = "".join(A_DIGITO.get(c, c) if not c.isdigit() else c for c in placa[:n_dig])
    cola = "".join(A_LETRA.get(c, c) if c.isdigit() else c for c in placa[n_dig:])
    return cabeza + cola


def _canon(c):
    """Clase de equivalencia de caracteres confundibles por OCR."""
    return A_LETRA.get(c, c)


def _distancia(a, b):
    """Levenshtein donde los caracteres confundibles por OCR cuestan 0."""
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            costo = 0 if _canon(ca) == _canon(cb) else 1
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + costo))
        prev = cur
    return prev[-1]


def sugerir(placa, candidatas, max_dist=1, limite=3):
    """Devuelve placas registradas parecidas (errores de OCR o 1 carácter distinto)."""
    out = []
    for c in candidatas:
        if c == placa:
            continue
        d = _distancia(placa, c)
        if d <= max_dist:
            out.append((d, c))
    out.sort()
    return [c for _, c in out[:limite]]
