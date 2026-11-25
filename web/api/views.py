from django.conf import settings
from google.auth.transport import requests as g_requests
from google.oauth2 import id_token as g_id_token
from drf_spectacular.utils import extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from core import agente, agente_llm, placas, services
from core.models import Ajuste, Alerta, Caseta, Paso, Tarifa, Usuario, Vehiculo

from .auth import emitir_token
from .permissions import AdminEscribe_TodosLeen, SoloAdmin
from .serializers import (AlertaSerializer, CasetaSerializer, ChatSerializer, ConsultarImagenSerializer,
                          ConsultarSerializer, FrameSerializer, GoogleLoginSerializer, PasoSerializer,
                          TarifaSerializer, UsuarioSerializer, VehiculoSerializer)


# --------------------------------------------------------------------------
# Autenticación
# --------------------------------------------------------------------------
class GoogleLoginView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    @extend_schema(request=GoogleLoginSerializer, responses={200: dict, 403: dict}, summary="Login con Google")
    def post(self, request):
        ser = GoogleLoginSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            info = None
            for client_id in settings.GOOGLE_CLIENT_IDS:
                try:
                    info = g_id_token.verify_oauth2_token(ser.validated_data["id_token"],
                                                          g_requests.Request(), client_id)
                    break
                except ValueError:
                    continue
            if info is None:
                raise ValueError("token no válido para ningún client id")
        except Exception:
            return Response({"detail": "Token de Google inválido."}, status=status.HTTP_401_UNAUTHORIZED)

        if not info.get("email_verified"):
            return Response({"detail": "El correo de Google no está verificado."}, status=status.HTTP_403_FORBIDDEN)

        email = info["email"].lower()
        usuario = Usuario.objects.filter(email_google__iexact=email, activo=True).first()
        if usuario is None:
            return Response({"detail": "Acceso denegado: tu cuenta de Google no está autorizada.",
                             "email": email}, status=status.HTTP_403_FORBIDDEN)
        if not usuario.nombre and info.get("name"):
            usuario.nombre = info["name"]
            usuario.save(update_fields=["nombre"])
        return Response({"token": emitir_token(usuario), "usuario": UsuarioSerializer(usuario).data})


class AjusteInferenciaView(APIView):
    """URL y API key del endpoint de inferencia, editables por el administrador sin tocar el servidor."""
    permission_classes = [SoloAdmin]

    def _estado(self):
        panel = Ajuste.objects.filter(clave="inference_url").exclude(valor="").exists()
        return {"url": services.inference_url(), "origen": "panel" if panel else ".env",
                "api_key_configurada": bool(services.inference_key())}

    @extend_schema(responses=dict, summary="Ajustes del endpoint de inferencia")
    def get(self, request):
        return Response(self._estado())

    @extend_schema(request=dict, responses=dict, summary="Cambiar URL y/o API key del endpoint de inferencia")
    def put(self, request):
        url = (request.data.get("url") or "").strip().rstrip("/")
        error = services.url_permitida(url) if url else "Falta la URL."
        if error:
            return Response({"detail": error}, status=status.HTTP_400_BAD_REQUEST)
        Ajuste.objects.update_or_create(clave="inference_url", defaults={"valor": url})
        if "api_key" in request.data:
            Ajuste.objects.update_or_create(clave="inference_api_key",
                                            defaults={"valor": (request.data.get("api_key") or "").strip()})
        return Response({**self._estado(), "prueba": services.estado_inferencia()})


class AjusteLLMView(APIView):
    """Modelo de lenguaje del agente (API compatible con OpenAI), editable desde el panel."""
    permission_classes = [SoloAdmin]

    def _estado(self):
        c = agente_llm.config()
        return {"url": c["url"], "modelo": c["modelo"], "api_key_configurada": bool(c["clave"]),
                "activo": bool(c["url"])}

    @extend_schema(responses=dict, summary="Ajustes del LLM del agente")
    def get(self, request):
        return Response(self._estado())

    @extend_schema(request=dict, responses=dict, summary="Cambiar URL base, modelo y/o API key del LLM")
    def put(self, request):
        for campo, clave in (("url", "llm_base_url"), ("modelo", "llm_model"), ("api_key", "llm_api_key")):
            if campo in request.data:
                v = (request.data.get(campo) or "").strip()
                Ajuste.objects.update_or_create(clave=clave, defaults={"valor": v.rstrip("/") if campo == "url" else v})
        resultado = self._estado()
        if resultado["activo"]:
            try:
                resultado["prueba"] = {"ok": True, "respuesta": agente_llm.responder("Responde solo: ok")["texto"][:80]}
            except Exception as e:
                resultado["prueba"] = {"ok": False, "detalle": str(e)[:200]}
        return Response(resultado)


class ConfigPublicaView(APIView):
    """Datos públicos que necesita el front antes de iniciar sesión (el client id de Google no es secreto)."""
    authentication_classes = []
    permission_classes = [AllowAny]

    @extend_schema(responses=dict, summary="Configuración pública del front")
    def get(self, request):
        return Response({"google_client_id": settings.GOOGLE_CLIENT_IDS[0] if settings.GOOGLE_CLIENT_IDS else ""})


class YoView(APIView):
    @extend_schema(responses=UsuarioSerializer, summary="Usuario autenticado")
    def get(self, request):
        return Response(UsuarioSerializer(request.user).data)


# --------------------------------------------------------------------------
# CRUD
# --------------------------------------------------------------------------
class VehiculoViewSet(viewsets.ModelViewSet):
    queryset = Vehiculo.objects.all()
    serializer_class = VehiculoSerializer
    permission_classes = [AdminEscribe_TodosLeen]

    def get_queryset(self):
        qs = super().get_queryset()
        q = self.request.query_params.get("q")
        if q:
            qs = qs.filter(placa__icontains=placas.normalizar(q))
        return qs


class CasetaViewSet(viewsets.ModelViewSet):
    queryset = Caseta.objects.all()
    serializer_class = CasetaSerializer
    permission_classes = [AdminEscribe_TodosLeen]

    @extend_schema(responses=dict, summary="Conteo y recaudación del día")
    @action(detail=True, methods=["get"])
    def resumen(self, request, pk=None):
        caseta = self.get_object()
        return Response(services.resumen_caseta(caseta.id))


class TarifaViewSet(viewsets.ModelViewSet):
    queryset = Tarifa.objects.all()
    serializer_class = TarifaSerializer
    permission_classes = [AdminEscribe_TodosLeen]


class UsuarioViewSet(viewsets.ModelViewSet):
    """Gestión de la lista blanca (solo administradores)."""
    queryset = Usuario.objects.all().order_by("email_google")
    serializer_class = UsuarioSerializer
    permission_classes = [SoloAdmin]


class PasoViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Paso.objects.select_related("caseta").all()
    serializer_class = PasoSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        p = self.request.query_params
        if p.get("placa"):
            qs = qs.filter(placa_normalizada__icontains=placas.normalizar(p["placa"]))
        if p.get("estado"):
            qs = qs.filter(estado=p["estado"])
        if p.get("caseta"):
            qs = qs.filter(caseta_id=p["caseta"])
        return qs


class AlertaViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Alerta.objects.select_related("paso", "paso__caseta").all()
    serializer_class = AlertaSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        if self.request.query_params.get("atendida") in ("0", "false"):
            qs = qs.filter(atendida=False)
        return qs

    @extend_schema(request=None, responses=AlertaSerializer, summary="Marcar alerta como atendida")
    @action(detail=True, methods=["post"])
    def atender(self, request, pk=None):
        a = self.get_object()
        a.atendida = True
        a.save(update_fields=["atendida"])
        return Response(AlertaSerializer(a).data)


# --------------------------------------------------------------------------
# Flujo del peaje
# --------------------------------------------------------------------------
class PasoFrameView(APIView):
    parser_classes = [MultiPartParser, FormParser]

    @extend_schema(request={"multipart/form-data": FrameSerializer}, responses=dict,
                   summary="Recibe un frame, infiere, registra el paso y lo emite en tiempo real")
    def post(self, request):
        ser = FrameSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            caseta = Caseta.objects.get(pk=ser.validated_data["caseta_id"])
        except Caseta.DoesNotExist:
            return Response({"detail": "Caseta no existe."}, status=status.HTTP_404_NOT_FOUND)
        try:
            data = services.registrar_frame(ser.validated_data["imagen"].read(), caseta, request.user)
        except services.InferenciaError as e:
            return Response({"detail": str(e)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        return Response(data)


class ConsultarPlacaView(APIView):
    @extend_schema(request=ConsultarSerializer, responses=dict, summary="Consulta una placa por texto")
    def post(self, request):
        ser = ConsultarSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        return Response(services.estado_de_placa(ser.validated_data["placa"]))


class ConsultarImagenView(APIView):
    parser_classes = [MultiPartParser, FormParser]

    @extend_schema(request={"multipart/form-data": ConsultarImagenSerializer}, responses=dict,
                   summary="Consulta una placa por imagen (M1 + OCR)")
    def post(self, request):
        ser = ConsultarImagenSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        r = agente.responder(imagen_bytes=ser.validated_data["imagen"].read())
        if r["estado"] == "error_inferencia":
            return Response({"detail": r["respuesta"]}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        if r["estado"] == "imagen_ilegible":
            return Response({"estado": "imagen_ilegible", "mensaje": r["respuesta"]},
                            status=status.HTTP_422_UNPROCESSABLE_ENTITY)
        return Response(r["datos"])


class HistorialPlacaView(APIView):
    @extend_schema(responses=PasoSerializer(many=True), summary="Historial de pasos de una placa")
    def get(self, request, placa):
        p = placas.normalizar(placa)
        qs = Paso.objects.filter(placa_normalizada=p).select_related("caseta")
        return Response({"placa": p, "total": qs.count(), "pasos": PasoSerializer(qs, many=True).data})


class AgenteChatView(APIView):
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    @extend_schema(request=ChatSerializer, responses=dict, summary="Mensaje al agente conversacional")
    def post(self, request):
        ser = ChatSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        img = ser.validated_data.get("imagen")
        r = agente.responder(ser.validated_data.get("mensaje", ""), img.read() if img else None)
        return Response(r)


class EstadoInferenciaView(APIView):
    @extend_schema(responses=dict, summary="Indica si el endpoint de inferencia responde")
    def get(self, request):
        return Response(services.estado_inferencia())


class ResumenGlobalView(APIView):
    @extend_schema(responses=dict, summary="Contadores del panel (todas las casetas, hoy)")
    def get(self, request):
        res = [services.resumen_caseta(c.id) for c in Caseta.objects.all()]
        return Response({
            "pasos": sum(r["pasos"] for r in res),
            "recaudacion": str(sum(float(r["recaudacion"]) for r in res)),
            "alertas": sum(r["alertas"] for r in res),
            "alertas_pendientes": Alerta.objects.filter(atendida=False).count(),
            "casetas": res,
        })
