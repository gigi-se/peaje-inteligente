from django.db import models


class Usuario(models.Model):
    """Lista blanca de cuentas de Google. No hay contraseñas."""

    ROL_ADMIN = "admin"
    ROL_OPERADOR = "operador"
    ROLES = [(ROL_ADMIN, "Administrador"), (ROL_OPERADOR, "Operador")]

    email_google = models.EmailField(unique=True)
    nombre = models.CharField(max_length=150, blank=True)
    rol = models.CharField(max_length=10, choices=ROLES, default=ROL_OPERADOR)
    activo = models.BooleanField(default=True)

    class Meta:
        db_table = "usuarios"

    # Requeridos por DRF para tratar este objeto como "request.user"
    @property
    def is_authenticated(self):
        return True

    @property
    def es_admin(self):
        return self.rol == self.ROL_ADMIN

    def __str__(self):
        return f"{self.email_google} ({self.rol})"


class Caseta(models.Model):
    nombre = models.CharField(max_length=100)
    ubicacion = models.CharField(max_length=200, blank=True)

    class Meta:
        db_table = "casetas"

    def __str__(self):
        return self.nombre


class Vehiculo(models.Model):
    CATEGORIAS = [
        ("moto", "Moto"),
        ("auto", "Auto"),
        ("minibus", "Minibús"),
        ("microbus", "Micro"),
        ("camion", "Camión"),
        ("bus", "Bus"),
    ]

    placa = models.CharField(max_length=10, unique=True, help_text="Normalizada: mayúsculas, sin guiones ni espacios")
    propietario = models.CharField(max_length=150)
    categoria = models.CharField(max_length=10, choices=CATEGORIAS)
    ejes = models.PositiveSmallIntegerField(default=2)
    saldo = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    activo = models.BooleanField(default=True)

    class Meta:
        db_table = "vehiculos"
        ordering = ["placa"]

    def save(self, *args, **kwargs):
        from .placas import normalizar

        self.placa = normalizar(self.placa)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.placa


class Tarifa(models.Model):
    """ejes = 0 significa 'cualquier número de ejes' para esa categoría."""

    categoria = models.CharField(max_length=10, choices=Vehiculo.CATEGORIAS)
    ejes = models.PositiveSmallIntegerField(default=0)
    monto = models.DecimalField(max_digits=8, decimal_places=2)

    class Meta:
        db_table = "tarifas"
        unique_together = [("categoria", "ejes")]
        ordering = ["categoria", "ejes"]

    def __str__(self):
        return f"{self.categoria}/{self.ejes} ejes = {self.monto}"


class Paso(models.Model):
    ESTADO_OK = "ok"
    ESTADO_NO_REGISTRADA = "no_registrada"
    ESTADO_SIN_SALDO = "sin_saldo"
    ESTADOS = [
        (ESTADO_OK, "Cobrado"),
        (ESTADO_NO_REGISTRADA, "Placa no registrada"),
        (ESTADO_SIN_SALDO, "Sin saldo"),
    ]

    placa_leida = models.CharField(max_length=20)
    placa_normalizada = models.CharField(max_length=10, db_index=True)
    confianza_ocr = models.FloatField(default=0)
    categoria_detectada = models.CharField(max_length=10, blank=True)
    ejes_detectados = models.PositiveSmallIntegerField(default=0)
    monto = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    caseta = models.ForeignKey(Caseta, on_delete=models.PROTECT, related_name="pasos")
    usuario = models.ForeignKey(Usuario, null=True, on_delete=models.SET_NULL, related_name="pasos")
    imagen_url = models.CharField(max_length=300, blank=True)
    estado = models.CharField(max_length=15, choices=ESTADOS)
    latencia_ms = models.FloatField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "pasos"
        ordering = ["-created_at"]


class Ajuste(models.Model):
    """Ajustes que el administrador cambia desde el panel (p. ej. URL y clave del endpoint de inferencia)."""

    clave = models.CharField(max_length=50, unique=True)
    valor = models.TextField(blank=True)

    class Meta:
        db_table = "ajustes"


class Alerta(models.Model):
    TIPO_NO_REGISTRADA = "no_registrada"
    TIPO_SIN_SALDO = "sin_saldo"
    TIPOS = [(TIPO_NO_REGISTRADA, "Placa no registrada"), (TIPO_SIN_SALDO, "Sin saldo")]

    paso = models.ForeignKey(Paso, on_delete=models.CASCADE, related_name="alertas")
    tipo = models.CharField(max_length=15, choices=TIPOS)
    atendida = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "alertas"
        ordering = ["-created_at"]
