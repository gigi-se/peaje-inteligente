import datetime

import jwt
from django.conf import settings
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed

from core.models import Usuario


def emitir_token(usuario):
    ahora = datetime.datetime.now(datetime.timezone.utc)
    payload = {
        "sub": str(usuario.id),
        "email": usuario.email_google,
        "rol": usuario.rol,
        "iat": ahora,
        "exp": ahora + datetime.timedelta(hours=settings.JWT_HORAS),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")


def usuario_desde_token(token):
    """Devuelve el Usuario activo del token, o None si es inválido/expirado/desautorizado."""
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
    except jwt.PyJWTError:
        return None
    return Usuario.objects.filter(pk=payload.get("sub"), activo=True).first()


class JWTAuthentication(BaseAuthentication):
    """Authorization: Bearer <token propio emitido tras el login con Google>."""

    def authenticate(self, request):
        cab = request.headers.get("Authorization", "")
        if not cab.startswith("Bearer "):
            return None
        usuario = usuario_desde_token(cab[7:])
        if usuario is None:
            raise AuthenticationFailed("Token inválido o cuenta no autorizada.")
        return (usuario, None)

    def authenticate_header(self, request):
        return "Bearer"
