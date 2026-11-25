from django.urls import path

from .consumers import PeajeConsumer

websocket_urlpatterns = [path("ws/peaje/", PeajeConsumer.as_asgi())]
