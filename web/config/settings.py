"""Configuración de Django para el Sistema de Control de Peaje.

Todo se lee de variables de entorno (archivo .env en la raíz del repo).
Nunca se escriben credenciales aquí.
"""
import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR.parent / ".env")


def env(name, default=""):
    return os.environ.get(name, default)


def env_bool(name, default=False):
    return env(name, str(default)).strip().lower() in ("1", "true", "yes", "si")


def env_list(name, default=""):
    return [x.strip() for x in env(name, default).split(",") if x.strip()]


# --- Seguridad -------------------------------------------------------------
SECRET_KEY = env("DJANGO_SECRET_KEY", "inseguro-solo-desarrollo")
DEBUG = env_bool("DJANGO_DEBUG", False)
ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", "localhost")
CSRF_TRUSTED_ORIGINS = env_list("CSRF_TRUSTED_ORIGINS", "")
# Nginx termina HTTPS y reenvía a Daphne por HTTP
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# --- Apps ------------------------------------------------------------------
# Sin django.contrib.auth/admin a propósito: no hay usuarios con contraseña,
# el acceso es exclusivamente con Google (lista blanca en la tabla usuarios).
INSTALLED_APPS = [
    "daphne",
    "django.contrib.contenttypes",
    "django.contrib.staticfiles",
    "corsheaders",
    "rest_framework",
    "drf_spectacular",
    "channels",
    "core",
    "api",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.common.CommonMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"
TEMPLATES = [
    {"BACKEND": "django.template.backends.django.DjangoTemplates", "DIRS": [], "APP_DIRS": True,
     "OPTIONS": {"context_processors": ["django.template.context_processors.request"]}},
]

# --- Base de datos ---------------------------------------------------------
# DB_ENGINE=sqlite solo para pruebas rápidas. En producción: postgres.
if env("DB_ENGINE", "postgres") == "sqlite":
    DATABASES = {
        "default": {"ENGINE": "django.db.backends.sqlite3", "NAME": BASE_DIR / "db.sqlite3"}
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": env("DB_NAME", "peaje"),
            "USER": env("DB_USER", "peaje"),
            "PASSWORD": env("DB_PASSWORD"),
            "HOST": env("DB_HOST", "localhost"),
            "PORT": env("DB_PORT", "5432"),
            "CONN_MAX_AGE": 60,
        }
    }
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- Tiempo real (Django Channels) ----------------------------------------
REDIS_URL = env("REDIS_URL", "")
if REDIS_URL:
    CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels_redis.core.RedisChannelLayer",
            "CONFIG": {"hosts": [REDIS_URL]},
        }
    }
else:  # solo pruebas
    CHANNEL_LAYERS = {"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}}

# --- DRF -------------------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ["api.auth.JWTAuthentication"],
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_PAGINATION_CLASS": "api.pagination.Paginacion",
    "UNAUTHENTICATED_USER": None,
}
SPECTACULAR_SETTINGS = {
    "TITLE": "API Sistema Inteligente de Control de Peaje",
    "DESCRIPTION": "Autenticación con Google; todas las rutas (excepto /auth/google) requieren Bearer token.",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
}

CORS_ALLOWED_ORIGINS = env_list("CORS_ALLOWED_ORIGINS", "http://localhost:5173")

# --- Estáticos y media -----------------------------------------------------
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"
DATA_UPLOAD_MAX_MEMORY_SIZE = 20 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 20 * 1024 * 1024

LANGUAGE_CODE = "es"
TIME_ZONE = "America/La_Paz"
USE_TZ = True

# --- Configuración propia del peaje ---------------------------------------
PUBLIC_BASE_URL = env("PUBLIC_BASE_URL", "").rstrip("/")

# Google: se aceptan los ID tokens emitidos para el cliente web o el Android
GOOGLE_CLIENT_IDS = [
    c for c in (env("GOOGLE_CLIENT_ID_WEB"), env("GOOGLE_CLIENT_ID_ANDROID")) if c
]

JWT_SECRET = env("JWT_SECRET", SECRET_KEY)
JWT_HORAS = int(env("JWT_HORAS", "12"))

ADMIN_EMAIL = env("ADMIN_EMAIL", "doc.alvaro.pinto.ma@unifranz.edu.bo")
EXTRA_ADMIN_EMAILS = env_list("EXTRA_ADMIN_EMAILS", "")
OPERADOR_EMAILS = env_list("OPERADOR_EMAILS", "")

# Endpoint de inferencia (RunPod o Colab): cambiar solo esta variable
INFERENCE_URL = env("INFERENCE_URL", "").rstrip("/")
INFERENCE_API_KEY = env("INFERENCE_API_KEY", "")
INFERENCE_TIMEOUT = int(env("INFERENCE_TIMEOUT", "30"))

# Un mismo vehículo visto varias veces seguidas en la misma caseta
# (frames a 2-5 fps) se registra una sola vez dentro de esta ventana.
DEDUP_SEGUNDOS = int(env("DEDUP_SEGUNDOS", "30"))
# Confianza mínima del OCR para aceptar una lectura de placa
OCR_CONFIANZA_MIN = float(env("OCR_CONFIANZA_MIN", "0.40"))

# Agente conversacional (LLM con function calling, compatible OpenAI)
LLM_BASE_URL = env("LLM_BASE_URL", "")
LLM_MODEL = env("LLM_MODEL", "qwen2.5")
LLM_API_KEY = env("LLM_API_KEY", "")
