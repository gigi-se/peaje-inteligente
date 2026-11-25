from io import BytesIO
from unittest import mock

from asgiref.sync import sync_to_async
from channels.testing import WebsocketCommunicator
from django.core.management import call_command
from django.test import TestCase, override_settings
from PIL import Image
from rest_framework.test import APIClient

from api.auth import emitir_token
from core import placas
from core.models import Alerta, Paso, Usuario, Vehiculo


def jpg():
    b = BytesIO()
    Image.new("RGB", (64, 64), "white").save(b, "JPEG")
    b.seek(0)
    b.name = "f.jpg"
    return b


def fake_inferencia(placa="2481KLM", conf=0.9, cat="auto", ejes=2):
    return {"placa_leida": placa, "confianza": conf, "categoria": cat, "ejes": ejes,
            "latencia_ms": 100.0, "latencia_total_ms": 120.0}


class PlacasTests(TestCase):
    def test_normalizar_y_validar(self):
        self.assertEqual(placas.normalizar(" 2481-klm "), "2481KLM")
        self.assertTrue(placas.es_valida("2481KLM"))
        self.assertTrue(placas.es_valida("123ABC"))
        self.assertFalse(placas.es_valida("ABC1234"))

    def test_correccion_ocr_por_posicion(self):
        self.assertEqual(placas.corregir_ocr("2481KLM"), "2481KLM")
        self.assertEqual(placas.corregir_ocr("248IKLM"), "2481KLM")   # I -> 1
        self.assertEqual(placas.corregir_ocr("2481K1M"), "2481KIM")   # 1 -> I
        self.assertEqual(placas.corregir_ocr("S481KLM"), "5481KLM")   # S -> 5

    def test_sugerencias(self):
        self.assertEqual(placas.sugerir("2481KLM", ["2481KLN", "9999ZZZ"]), ["2481KLN"])


@override_settings(DEDUP_SEGUNDOS=30, INFERENCE_URL="http://x")
class FlujoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed", verbosity=0)
        cls.admin = Usuario.objects.get(email_google="doc.alvaro.pinto.ma@unifranz.edu.bo")
        cls.oper = Usuario.objects.create(email_google="op@x.com", rol="operador")

    def setUp(self):
        self.c = APIClient()
        self.c.credentials(HTTP_AUTHORIZATION="Bearer " + emitir_token(self.oper))

    def test_seed(self):
        self.assertGreaterEqual(Vehiculo.objects.count(), 20)
        self.assertEqual(self.admin.rol, "admin")
        call_command("seed", verbosity=0)  # idempotente
        self.assertEqual(Vehiculo.objects.count(), 20)

    def test_rutas_exigen_autenticacion(self):
        anon = APIClient()
        for url in ["/api/v1/vehiculos/", "/api/v1/pasos/", "/api/v1/alertas/", "/api/v1/estado",
                    "/api/v1/casetas/1/resumen/", "/api/v1/placas/2481KLM/historial"]:
            self.assertEqual(anon.get(url).status_code, 401, url)
        for url in ["/api/v1/pasos/frame", "/api/v1/placas/consultar", "/api/v1/agente/chat"]:
            self.assertEqual(anon.post(url, {}).status_code, 401, url)

    def test_token_invalido_o_usuario_inactivo(self):
        c = APIClient()
        c.credentials(HTTP_AUTHORIZATION="Bearer basura")
        self.assertEqual(c.get("/api/v1/vehiculos/").status_code, 401)
        self.oper.activo = False
        self.oper.save()
        self.assertEqual(self.c.get("/api/v1/vehiculos/").status_code, 401)

    def test_login_google_rechaza_no_autorizado(self):
        info = {"email": "intruso@gmail.com", "email_verified": True, "name": "X"}
        with override_settings(GOOGLE_CLIENT_IDS=["cid"]), \
                mock.patch("api.views.g_id_token.verify_oauth2_token", return_value=info):
            r = APIClient().post("/api/v1/auth/google", {"id_token": "t"}, format="json")
        self.assertEqual(r.status_code, 403)
        info["email"] = "DOC.ALVARO.PINTO.MA@unifranz.edu.bo"
        with override_settings(GOOGLE_CLIENT_IDS=["cid"]), \
                mock.patch("api.views.g_id_token.verify_oauth2_token", return_value=info):
            r = APIClient().post("/api/v1/auth/google", {"id_token": "t"}, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["usuario"]["rol"], "admin")

    def test_operador_no_escribe_vehiculos_admin_si(self):
        datos = {"placa": "1111AAA", "propietario": "T", "categoria": "auto", "ejes": 2, "saldo": "10"}
        self.assertEqual(self.c.post("/api/v1/vehiculos/", datos, format="json").status_code, 403)
        ca = APIClient()
        ca.credentials(HTTP_AUTHORIZATION="Bearer " + emitir_token(self.admin))
        self.assertEqual(ca.post("/api/v1/vehiculos/", datos, format="json").status_code, 201)

    def frame(self, **kw):
        with mock.patch("core.services.inferir", return_value=fake_inferencia(**kw)):
            return self.c.post("/api/v1/pasos/frame", {"imagen": jpg(), "caseta_id": 1}, format="multipart")

    def test_paso_registrado_cobra_y_deduplica(self):
        saldo0 = Vehiculo.objects.get(placa="2481KLM").saldo
        r = self.frame()
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(r.json()["paso"]["estado"], "ok")
        self.assertEqual(Vehiculo.objects.get(placa="2481KLM").saldo, saldo0 - 5)
        r2 = self.frame()                       # mismo frame segundos después
        self.assertTrue(r2.json()["duplicado"])
        self.assertEqual(Paso.objects.count(), 1)

    def test_placa_no_registrada_genera_alerta(self):
        r = self.frame(placa="9999ZZZ")
        self.assertEqual(r.json()["paso"]["estado"], "no_registrada")
        self.assertEqual(Alerta.objects.get().tipo, "no_registrada")

    def test_sin_saldo_genera_alerta_y_no_cobra(self):
        r = self.frame(placa="3920TRX")         # saldo 3 < tarifa auto 5
        self.assertEqual(r.json()["paso"]["estado"], "sin_saldo")
        self.assertEqual(Vehiculo.objects.get(placa="3920TRX").saldo, 3)
        self.assertEqual(Alerta.objects.get().tipo, "sin_saldo")

    def test_tarifa_camion_por_ejes(self):
        r = self.frame(placa="8284XSW", cat="camion", ejes=3)
        self.assertEqual(r.json()["tarifa"], "25.00")

    def test_placa_ilegible_no_registra(self):
        r = self.frame(placa="??", conf=0.2)
        self.assertFalse(r.json()["detectado"])
        self.assertEqual(Paso.objects.count(), 0)

    def test_cuatro_estados(self):
        q = lambda p: self.c.post("/api/v1/placas/consultar", {"placa": p}, format="json").json()
        self.assertEqual(q("2481-KLM")["estado"], "registrada_sin_paso")
        self.frame()
        self.assertEqual(q("2481 klm")["estado"], "registrada_con_paso")
        self.frame(placa="9999ZZZ")
        self.assertEqual(q("9999ZZZ")["estado"], "identificada_no_registrada")
        r = q("5555QQQ")
        self.assertEqual(r["estado"], "no_existe")
        self.assertEqual(q("hola")["estado"], "formato_invalido")

    def test_sugerencia_por_ocr_en_no_existe(self):
        r = self.c.post("/api/v1/placas/consultar", {"placa": "2481KLN"}, format="json").json()
        self.assertEqual(r["estado"], "no_existe")
        self.assertIn("2481KLM", r["sugerencias"])

    def test_agente_texto_e_imagen_ilegible(self):
        r = self.c.post("/api/v1/agente/chat", {"mensaje": "¿qué pasa con la placa 2481-KLM?"}, format="json").json()
        self.assertEqual(r["estado"], "registrada_sin_paso")
        with mock.patch("core.services.inferir", return_value=fake_inferencia(placa="", conf=0.0)):
            r = self.c.post("/api/v1/agente/chat", {"imagen": jpg()}, format="multipart").json()
        self.assertEqual(r["estado"], "imagen_ilegible")

    def test_resumen_y_historial(self):
        self.frame()
        self.assertEqual(self.c.get("/api/v1/casetas/1/resumen/").json()["pasos"], 1)
        h = self.c.get("/api/v1/placas/2481KLM/historial").json()
        self.assertEqual(h["total"], 1)

    def test_inferencia_caida_devuelve_503(self):
        with mock.patch("core.services.requests.post", side_effect=__import__("requests").ConnectionError("x")):
            r = self.c.post("/api/v1/pasos/frame", {"imagen": jpg(), "caseta_id": 1}, format="multipart")
        self.assertEqual(r.status_code, 503)


class RealtimeTests(TestCase):
    """El panel recibe eventos por WebSocket sin recargar."""

    @classmethod
    def setUpTestData(cls):
        call_command("seed", verbosity=0)

    async def test_ws_recibe_paso_y_rechaza_token_malo(self):
        from config.asgi import application
        from core.realtime import emitir

        malo = WebsocketCommunicator(application, "/ws/peaje/?token=basura")
        ok, _ = await malo.connect()
        self.assertFalse(ok)

        u = await sync_to_async(Usuario.objects.first)()
        token = emitir_token(u)
        com = WebsocketCommunicator(application, f"/ws/peaje/?token={token}")
        ok, _ = await com.connect()
        self.assertTrue(ok)
        await sync_to_async(emitir)("paso.nuevo", {"placa": "2481KLM"})
        msg = await com.receive_json_from()
        self.assertEqual(msg, {"tipo": "paso.nuevo", "data": {"placa": "2481KLM"}})
        await com.disconnect()

    def test_config_publica_sin_login(self):
        with override_settings(GOOGLE_CLIENT_IDS=["abc.apps.googleusercontent.com"]):
            r = APIClient().get("/api/v1/config")
        self.assertEqual(r.json()["google_client_id"], "abc.apps.googleusercontent.com")


@override_settings(INFERENCE_URL="https://env.trycloudflare.com", INFERENCE_API_KEY="clave-env")
class AjustesInferenciaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed", verbosity=0)
        cls.admin = Usuario.objects.get(email_google="doc.alvaro.pinto.ma@unifranz.edu.bo")
        cls.oper = Usuario.objects.create(email_google="op@x.com", rol="operador")

    def cli(self, u):
        c = APIClient()
        c.credentials(HTTP_AUTHORIZATION="Bearer " + emitir_token(u))
        return c

    def test_solo_admin(self):
        self.assertEqual(self.cli(self.oper).get("/api/v1/ajustes/inferencia").status_code, 403)
        self.assertEqual(self.cli(self.oper).put("/api/v1/ajustes/inferencia", {"url": "https://a.com"}, format="json").status_code, 403)
        self.assertEqual(APIClient().get("/api/v1/ajustes/inferencia").status_code, 401)

    def test_rechaza_localhost_y_privadas(self):
        for u in ["http://localhost:8000", "http://127.0.0.1:8000", "http://192.168.1.7:8000", "http://10.0.0.5", "ftp://x.com", "abc"]:
            r = self.cli(self.admin).put("/api/v1/ajustes/inferencia", {"url": u}, format="json")
            self.assertEqual(r.status_code, 400, u)

    def test_panel_tiene_prioridad_sobre_env_y_se_usa(self):
        c = self.cli(self.admin)
        self.assertEqual(c.get("/api/v1/ajustes/inferencia").json()["origen"], ".env")
        with mock.patch("core.services.requests.get") as g:
            g.return_value = mock.Mock(status_code=200, ok=True, json=lambda: {"ok": True})
            r = c.put("/api/v1/ajustes/inferencia", {"url": "https://nuevo.trycloudflare.com/", "api_key": "k2"}, format="json")
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(r.json()["url"], "https://nuevo.trycloudflare.com")
        self.assertEqual(r.json()["origen"], "panel")
        self.assertNotIn("k2", r.content.decode())          # la clave nunca se devuelve
        with mock.patch("core.services.requests.post") as p:
            p.return_value = mock.Mock(json=lambda: {"placa": {"texto": "2481KLM", "confianza": 0.9},
                                                     "vehiculo": {"categoria": "auto"}, "ejes": 2}, raise_for_status=lambda: None)
            from core import services
            services.inferir(b"x")
        self.assertEqual(p.call_args.args[0], "https://nuevo.trycloudflare.com/predict")
        self.assertEqual(p.call_args.kwargs["headers"]["X-API-Key"], "k2")

    def test_estado_detecta_clave_rechazada(self):
        from core import services
        with mock.patch("core.services.requests.get", return_value=mock.Mock(status_code=401, ok=False)):
            e = services.estado_inferencia()
        self.assertFalse(e["ok"])
        self.assertIn("API key", e["detalle"])


class AgenteLLMTests(TestCase):
    def test_llm_con_herramientas_y_respaldo(self):
        from unittest import mock
        from core import agente, agente_llm
        from core.models import Ajuste, Vehiculo
        Vehiculo.objects.create(placa="2481KLM", propietario="Ana", categoria="auto", ejes=2)
        Ajuste.objects.create(clave="llm_base_url", valor="https://llm.example/v1")
        respuestas = iter([
            {"content": "", "tool_calls": [{"id": "1", "function": {"name": "consultar_placa", "arguments": '{"placa":"2481-KLM"}'}}]},
            {"content": "La placa 2481KLM es de Ana y nunca pasó."},
        ])
        vistos = []
        def falso(cfg, msgs):
            vistos.append(list(msgs)); return next(respuestas)
        with mock.patch.object(agente_llm, "_llamar", falso):
            r = agente.responder("estado de 2481KLM")
        self.assertEqual(r["motor"], "llm")
        self.assertIn("Ana", r["respuesta"])
        self.assertIn("Ana", vistos[1][-1]["content"])          # el resultado de la herramienta llegó de la BD
        with mock.patch.object(agente_llm, "_llamar", side_effect=RuntimeError("caído")):
            r = agente.responder("estado de 2481KLM")
        self.assertEqual(r["motor"], "reglas")                   # respaldo determinista
        self.assertIn("2481KLM", r["respuesta"])
