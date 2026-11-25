"""Mide la precisión del OCR de placas (dato obligatorio del informe).

Uso:   python evaluar_ocr.py carpeta_imagenes etiquetas.csv [fastplate easyocr]
etiquetas.csv:  archivo,placa      (ej.  foto01.jpg,2481KLM)
Reporta por motor: placas exactas, precisión por carácter, sin lectura y latencia media.
"""
import csv
import sys
import time
from pathlib import Path

import cv2

from m1_placas import M1, limpiar


def distancia(a, b):
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    carpeta, csv_path = Path(sys.argv[1]), sys.argv[2]
    motores = sys.argv[3:] or ["fastplate"]
    verdad = [(r["archivo"], limpiar(r["placa"])) for r in csv.DictReader(open(csv_path, encoding="utf-8"))]
    print(f"{len(verdad)} imágenes con etiqueta\n")
    print("| Motor | Placas exactas | Precisión por carácter | Sin lectura | Latencia media |")
    print("|---|---|---|---|---|")
    for motor in motores:
        m1 = M1(motor)
        exactas = sin = chars_ok = chars = 0
        ms = []
        errores = []
        for archivo, real in verdad:
            img = cv2.imread(str(carpeta / archivo))
            if img is None:
                print(f"  (no se pudo leer {archivo})")
                continue
            t0 = time.perf_counter()
            leida = m1.leer(img)["texto"]
            ms.append((time.perf_counter() - t0) * 1000)
            sin += leida == ""
            exactas += leida == real
            chars += len(real)
            chars_ok += max(0, len(real) - distancia(leida, real))
            if leida != real:
                errores.append((archivo, real, leida))
        n = max(1, len(verdad))
        print(f"| {motor} | {exactas}/{len(verdad)} ({100 * exactas / n:.1f} %) | {100 * chars_ok / max(1, chars):.1f} % "
              f"| {sin} | {sum(ms) / max(1, len(ms)):.0f} ms |")
        for a, r, l in errores:
            print(f"    - {a}: real={r} leída={l or '(nada)'}")


if __name__ == "__main__":
    main()
