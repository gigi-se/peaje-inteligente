from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("vehiculos", views.VehiculoViewSet)
router.register("casetas", views.CasetaViewSet)          # incluye /casetas/{id}/resumen/
router.register("tarifas", views.TarifaViewSet)
router.register("usuarios", views.UsuarioViewSet)
router.register("pasos", views.PasoViewSet)
router.register("alertas", views.AlertaViewSet)

urlpatterns = [
    path("auth/google", views.GoogleLoginView.as_view()),
    path("config", views.ConfigPublicaView.as_view()),
    path("auth/yo", views.YoView.as_view()),
    path("pasos/frame", views.PasoFrameView.as_view()),
    path("placas/consultar", views.ConsultarPlacaView.as_view()),
    path("placas/consultar-imagen", views.ConsultarImagenView.as_view()),
    path("placas/<str:placa>/historial", views.HistorialPlacaView.as_view()),
    path("agente/chat", views.AgenteChatView.as_view()),
    path("estado", views.EstadoInferenciaView.as_view()),
    path("ajustes/inferencia", views.AjusteInferenciaView.as_view()),
    path("ajustes/llm", views.AjusteLLMView.as_view()),
    path("resumen", views.ResumenGlobalView.as_view()),
    path("", include(router.urls)),
]
