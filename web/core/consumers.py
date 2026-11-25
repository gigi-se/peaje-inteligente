from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer

GRUPO = "peaje"


@database_sync_to_async
def _usuario_desde_token(token):
    from api.auth import usuario_desde_token

    return usuario_desde_token(token)


class PeajeConsumer(AsyncJsonWebsocketConsumer):
    """Canal en tiempo real del panel. Conexión: wss://dominio/ws/peaje/?token=<JWT>

    Eventos que emite: paso.nuevo, alerta.nueva, resumen.actualizado
    """

    async def connect(self):
        token = parse_qs(self.scope["query_string"].decode()).get("token", [""])[0]
        usuario = await _usuario_desde_token(token)
        if usuario is None:
            await self.close(code=4401)
            return
        self.usuario = usuario
        await self.channel_layer.group_add(GRUPO, self.channel_name)
        await self.accept()

    async def disconnect(self, code):
        await self.channel_layer.group_discard(GRUPO, self.channel_name)

    async def evento(self, event):
        await self.send_json({"tipo": event["tipo"], "data": event["data"]})
