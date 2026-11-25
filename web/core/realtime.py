from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from .consumers import GRUPO


def emitir(tipo, data):
    """Envía un evento a todos los paneles conectados."""
    layer = get_channel_layer()
    async_to_sync(layer.group_send)(GRUPO, {"type": "evento", "tipo": tipo, "data": data})
