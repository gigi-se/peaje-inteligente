from rest_framework import serializers

from core import placas
from core.models import Alerta, Caseta, Paso, Tarifa, Usuario, Vehiculo


class UsuarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Usuario
        fields = ["id", "email_google", "nombre", "rol", "activo"]


class CasetaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Caseta
        fields = ["id", "nombre", "ubicacion"]


class VehiculoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vehiculo
        fields = ["id", "placa", "propietario", "categoria", "ejes", "saldo", "activo"]

    def validate_placa(self, value):
        p = placas.normalizar(value)
        if not placas.es_valida(p):
            raise serializers.ValidationError("Formato inválido. Ej.: 2481KLM (3-4 dígitos + 3 letras).")
        qs = Vehiculo.objects.filter(placa=p)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("Ya existe un vehículo con esa placa.")
        return p


class TarifaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tarifa
        fields = ["id", "categoria", "ejes", "monto"]


class PasoSerializer(serializers.ModelSerializer):
    caseta_nombre = serializers.CharField(source="caseta.nombre", read_only=True)

    class Meta:
        model = Paso
        fields = ["id", "placa_leida", "placa_normalizada", "confianza_ocr", "categoria_detectada",
                  "ejes_detectados", "monto", "caseta", "caseta_nombre", "usuario", "imagen_url",
                  "estado", "latencia_ms", "created_at"]


class AlertaSerializer(serializers.ModelSerializer):
    paso = PasoSerializer(read_only=True)

    class Meta:
        model = Alerta
        fields = ["id", "tipo", "atendida", "created_at", "paso"]


# --- Entradas de los endpoints de acción ---
class GoogleLoginSerializer(serializers.Serializer):
    id_token = serializers.CharField()


class FrameSerializer(serializers.Serializer):
    imagen = serializers.ImageField()
    caseta_id = serializers.IntegerField()


class ConsultarSerializer(serializers.Serializer):
    placa = serializers.CharField(max_length=20)


class ConsultarImagenSerializer(serializers.Serializer):
    imagen = serializers.ImageField()


class ChatSerializer(serializers.Serializer):
    mensaje = serializers.CharField(required=False, allow_blank=True)
    imagen = serializers.ImageField(required=False)
