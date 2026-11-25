"""Métricas del sistema completo para el informe: placa, categoría, error en el conteo de ejes y latencia.

Uso:   python evaluar_pipeline.py carpeta_imagenes etiquetas.csv
etiquetas.csv:  archivo,placa,categoria,ejes     (las columnas placa/categoria/ejes son opcionales; deja vacío lo que no sepas)
   ej.:  camion01.jpg,1406VFR,camion,4
"""
import csv
import statistics
import sys
import time
from collections import Counter
from pathlib import Path


def evaluar(filas, carpeta, analizar_fn, leer_imagen):
    r = {"n": 0, "placa_ok": 0, "placa_n": 0, "placa_vacia": 0, "cat_ok": 0, "cat_n": 0, "ejes_n": 0, "ejes_ok": 0,
         "ejes_err_abs": 0.0, "ejes_nd": 0, "ms": [], "confusion": Counter(), "fallos_placa": [], "fallos_ejes": []}
    for f in filas:
        img = leer_imagen(Path(carpeta) / f["archivo"])
        if img is None:
            print(f"  (no se pudo leer {f['archivo']})")
            continue
        t0 = time.perf_counter()
        d = analizar_fn(img)
        r["ms"].append((time.perf_counter() - t0) * 1000)
        r["n"] += 1
        if f.get("placa"):
            real = "".join(c for c in f["placa"].upper() if c.isalnum())
            leida = d["placa"]["texto"]
            r["placa_n"] += 1
            r["placa_ok"] += leida == real
            r["placa_vacia"] += leida == ""
            if leida != real:
                r["fallos_placa"].append((f["archivo"], real, leida or "(nada)"))
        if f.get("categoria"):
            r["cat_n"] += 1
            r["cat_ok"] += d["vehiculo"]["categoria"] == f["categoria"]
            r["confusion"][(f["categoria"], d["vehiculo"]["categoria"] or "(ninguna)")] += 1
        if f.get("ejes"):
            real = int(f["ejes"])
            r["ejes_n"] += 1
            if d["ejes"] is None:
                r["ejes_nd"] += 1
                r["ejes_err_abs"] += real            # no determinar cuenta como error igual al número real de ejes
                r["fallos_ejes"].append((f["archivo"], real, "N/D"))
            else:
                r["ejes_ok"] += d["ejes"] == real
                r["ejes_err_abs"] += abs(d["ejes"] - real)
                if d["ejes"] != real:
                    r["fallos_ejes"].append((f["archivo"], real, d["ejes"]))
    return r


def informe(r):
    pct = lambda a, b: f"{100 * a / b:.1f} %" if b else "—"
    ms = sorted(r["ms"])
    lineas = [f"Imágenes evaluadas: {r['n']}", "",
              "| Métrica | Resultado |", "|---|---|",
              f"| Placa exacta (M1) | {r['placa_ok']}/{r['placa_n']} ({pct(r['placa_ok'], r['placa_n'])}), sin lectura: {r['placa_vacia']} |",
              f"| Categoría correcta (M2) | {r['cat_ok']}/{r['cat_n']} ({pct(r['cat_ok'], r['cat_n'])}) |",
              f"| Ejes exactos (M3) | {r['ejes_ok']}/{r['ejes_n']} ({pct(r['ejes_ok'], r['ejes_n'])}), no determinables: {r['ejes_nd']} |",
              f"| Error medio de ejes (MAE) | {r['ejes_err_abs'] / r['ejes_n']:.2f} ejes |" if r["ejes_n"] else "| Error medio de ejes (MAE) | — |"]
    if ms:
        p95 = ms[min(len(ms) - 1, int(0.95 * len(ms)))]
        lineas.append(f"| Latencia de inferencia | media {statistics.mean(ms):.0f} ms · p95 {p95:.0f} ms · máx {ms[-1]:.0f} ms |")
    if r["confusion"]:
        lineas += ["", "Matriz de confusión de categoría (real → predicha):"]
        lineas += [f"  {a} → {b}: {n}" for (a, b), n in sorted(r["confusion"].items())]
    for titulo, fallos in (("Placas falladas", r["fallos_placa"]), ("Ejes fallados", r["fallos_ejes"])):
        if fallos:
            lineas += ["", titulo + " (archivo, real, obtenido):"] + [f"  - {a}: {b} → {c}" for a, b, c in fallos]
    return "\n".join(lineas)


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    import cv2
    import app as servidor
    filas = list(csv.DictReader(open(sys.argv[2], encoding="utf-8")))
    servidor.cargar_modelos()
    print(informe(evaluar(filas, sys.argv[1], servidor.analizar, lambda p: cv2.imread(str(p)))))


if __name__ == "__main__":
    main()
