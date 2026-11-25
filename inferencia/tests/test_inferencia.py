"""Pruebas del endpoint de inferencia. M1 usa los modelos reales del docente; M2/M3 se simulan
(no requieren GPU ni pesos). Ejecutar:  python -m unittest discover -s tests -v   (desde /inferencia)"""
import sys
import unittest
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import app as servidor            # noqa: E402
import config                     # noqa: E402
from ejes_logic import contar_ejes   # noqa: E402
from m1_placas import M1, extraer_placa   # noqa: E402
from m2_vehiculos import elegir_vehiculo   # noqa: E402
from m3_ejes import kps_de_mascara, kps_desde_caja   # noqa: E402

IMAGEN = Path("/mnt/user-data/uploads/1795117755218_image.png")


def llanta(cx, cy, d, ancho=None, conf=0.9):
    a = d if ancho is None else ancho
    k = np.array([[cx, cy, conf], [cx, cy + d / 2, conf], [cx, cy - d / 2, conf],
                  [cx - a / 2, cy, conf], [cx + a / 2, cy, conf]], dtype=float)
    return {"conf": conf, "box": [cx - a / 2, cy - d / 2, cx + a / 2, cy + d / 2], "kps": k}


class TestEjes(unittest.TestCase):
    CAMION = [95, 255, 1037, 727]

    def test_camion_3_ejes_lateral(self):
        r = contar_ejes(self.CAMION, [llanta(170, 666, 100), llanta(270, 666, 100), llanta(680, 666, 100)])
        self.assertEqual(r["ejes"], 3)
        self.assertEqual(r["vista"], "lateral")
        self.assertEqual(len(r["llantas"]), 3)

    def test_ruedas_dobles_cuentan_un_eje(self):
        r = contar_ejes(self.CAMION, [llanta(170, 666, 100), llanta(215, 666, 100), llanta(680, 666, 100)])
        self.assertEqual(r["ejes"], 2)

    def test_llanta_lejana_pequena_se_descarta(self):
        r = contar_ejes(self.CAMION, [llanta(170, 666, 100), llanta(680, 666, 100), llanta(420, 650, 50)])
        self.assertEqual(r["ejes"], 2)

    def test_auto_2_ejes(self):
        r = contar_ejes([100, 300, 700, 560], [llanta(220, 530, 90), llanta(600, 530, 90)])
        self.assertEqual(r["ejes"], 2)

    def test_vista_frontal_no_determinable(self):
        r = contar_ejes([100, 100, 500, 450], [llanta(160, 420, 100, ancho=35), llanta(440, 420, 100, ancho=35)])
        self.assertIsNone(r["ejes"])
        self.assertEqual(r["vista"], "frontal/posterior")

    def test_sin_llantas(self):
        self.assertIsNone(contar_ejes(self.CAMION, [])["ejes"])

    def test_llanta_fuera_del_vehiculo_no_cuenta(self):
        r = contar_ejes(self.CAMION, [llanta(170, 666, 100), llanta(680, 666, 100), llanta(1500, 666, 100)])
        self.assertEqual(r["ejes"], 2)


class TestPlacas(unittest.TestCase):
    def test_extraer(self):
        casos = {"BOLIVIA2481KLM": "2481KLM", "2481-KLM": "2481KLM", "248IKLM": "2481KLM", "123ABC": "123ABC",
                 "ABC": "", "": "", "BOLIVIA": ""}
        for crudo, esperado in casos.items():
            self.assertEqual(extraer_placa(crudo)[0], esperado, crudo)

    def test_elegir_vehiculo(self):
        grande = {"categoria": "bus", "box": [0, 0, 1000, 800], "area": 0.5}
        auto = {"categoria": "auto", "box": [300, 300, 600, 600], "area": 0.1}
        self.assertEqual(elegir_vehiculo([grande, auto], [400, 450, 500, 500])["categoria"], "auto")
        self.assertEqual(elegir_vehiculo([grande, auto], None)["categoria"], "bus")
        self.assertIsNone(elegir_vehiculo([], None))

    def test_keypoints(self):
        m = np.zeros((200, 200), np.uint8)
        cv2.circle(m, (100, 120), 40, 1, -1)
        k = kps_de_mascara(m)
        self.assertAlmostEqual(k[0, 0], 100, delta=2)
        self.assertAlmostEqual(k[1, 1] - k[2, 1], 80, delta=3)     # contacto - superior = diámetro
        self.assertEqual(kps_desde_caja([0, 0, 100, 80]).shape, (5, 3))


class TestEvaluarPipeline(unittest.TestCase):
    def test_metricas(self):
        from evaluar_pipeline import evaluar, informe
        respuestas = iter([
            {"placa": {"texto": "2481KLM"}, "vehiculo": {"categoria": "auto"}, "ejes": 2},
            {"placa": {"texto": ""}, "vehiculo": {"categoria": "bus"}, "ejes": 3},
            {"placa": {"texto": "1406VFR"}, "vehiculo": {"categoria": "camion"}, "ejes": None},
        ])
        filas = [{"archivo": "a.jpg", "placa": "2481-KLM", "categoria": "auto", "ejes": "2"},
                 {"archivo": "b.jpg", "placa": "5951FGH", "categoria": "camion", "ejes": "2"},
                 {"archivo": "c.jpg", "placa": "1406VFR", "categoria": "camion", "ejes": "4"}]
        r = evaluar(filas, ".", lambda img: next(respuestas), lambda p: np.zeros((4, 4, 3), np.uint8))
        self.assertEqual((r["placa_ok"], r["placa_n"], r["placa_vacia"]), (2, 3, 1))
        self.assertEqual((r["cat_ok"], r["cat_n"]), (2, 3))
        self.assertEqual((r["ejes_ok"], r["ejes_n"], r["ejes_nd"]), (1, 3, 1))
        self.assertAlmostEqual(r["ejes_err_abs"], 0 + 1 + 4)      # 2 vs 2, 3 vs 2, N/D vs 4
        texto = informe(r)
        self.assertIn("2/3", texto)
        self.assertIn("camion → bus: 1", texto)


class FakeM2:
    def segmentar(self, img):
        h, w = img.shape[:2]
        return [{"categoria": "auto", "conf": 0.93, "box": [w * 0.12, h * 0.33, w * 0.51, h * 0.80], "area": 0.2}]


class FakeM3:
    def ejes(self, img, vbox):
        return contar_ejes(vbox, [llanta(vbox[0] + 40, vbox[3] - 30, 80), llanta(vbox[2] - 40, vbox[3] - 30, 80)])


@unittest.skipUnless(IMAGEN.exists(), "falta la imagen de referencia")
class TestAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from fastapi.testclient import TestClient
        servidor._modelos.clear()
        servidor._modelos.update(m1=M1(), m2=FakeM2(), m3=FakeM3())
        cls.c = TestClient(servidor.app)
        cls.jpg = cv2.imencode(".jpg", cv2.imread(str(IMAGEN)))[1].tobytes()

    def post(self, datos=None, **kw):
        return self.c.post("/predict", files={"file": ("f.jpg", datos or self.jpg, "image/jpeg")}, **kw)

    def test_predict_contrato(self):
        r = self.post()
        self.assertEqual(r.status_code, 200, r.text)
        d = r.json()
        self.assertEqual(d["placa"]["texto"], "2481KLM")
        self.assertGreater(d["placa"]["confianza"], 0.5)
        self.assertEqual(d["vehiculo"]["categoria"], "auto")
        self.assertEqual(d["ejes"], 2)
        self.assertEqual(len(d["keypoints"]), 2)
        self.assertIn("latencia_ms", d)

    def test_imagen_anotada_opcional(self):
        d = self.post(params={"anotada": "true"}).json()
        self.assertTrue(d["imagen_anotada"].startswith("data:image/jpeg;base64,"))

    def test_imagen_invalida_400(self):
        self.assertEqual(self.post(datos=b"no es imagen").status_code, 400)

    def test_api_key(self):
        config.API_KEY = "secreta"
        try:
            self.assertEqual(self.post().status_code, 401)
            self.assertEqual(self.post(headers={"X-API-Key": "secreta"}).status_code, 200)
        finally:
            config.API_KEY = ""

    def test_health(self):
        d = self.c.get("/health").json()
        self.assertTrue(d["ok"])

    def test_health_valida_la_clave(self):
        config.API_KEY = "secreta"
        try:
            self.assertEqual(self.c.get("/health").status_code, 401)
            self.assertEqual(self.c.get("/health", headers={"X-API-Key": "mala"}).status_code, 401)
            self.assertEqual(self.c.get("/health", headers={"X-API-Key": "secreta"}).status_code, 200)
        finally:
            config.API_KEY = ""

    def test_sin_placa_devuelve_vacio(self):
        blanca = cv2.imencode(".jpg", np.full((300, 400, 3), 255, np.uint8))[1].tobytes()
        d = self.post(datos=blanca).json()
        self.assertEqual(d["placa"]["texto"], "")


if __name__ == "__main__":
    unittest.main()
