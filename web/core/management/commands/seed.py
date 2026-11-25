"""Carga datos iniciales. Es idempotente: se puede ejecutar varias veces sin duplicar.

    python manage.py seed
"""
from decimal import Decimal

from django.conf import settings
from django.core.management.base import BaseCommand

from core.models import Caseta, Tarifa, Usuario, Vehiculo

TARIFAS = [
    # categoria, ejes (0 = cualquiera), monto en Bs
    ("moto", 0, "2.00"),
    ("auto", 0, "5.00"),
    ("minibus", 0, "8.00"),
    ("microbus", 0, "10.00"),
    ("bus", 0, "15.00"),
    ("camion", 2, "15.00"),
    ("camion", 3, "25.00"),
    ("camion", 4, "35.00"),
    ("camion", 5, "45.00"),
    ("camion", 6, "55.00"),
]

CASETAS = [("Caseta Norte", "Ruta La Paz - Oruro, km 12"), ("Caseta Sur", "Ruta La Paz - Copacabana, km 25")]

# 20 vehículos de prueba: placa, propietario, categoría, ejes, saldo
VEHICULOS = [
    ("2481KLM", "Carlos Mamani", "auto", 2, 150),
    ("1357ABC", "Lucía Quispe", "auto", 2, 80),
    ("3920TRX", "Jorge Choque", "auto", 2, 3),
    ("4412HJP", "María Flores", "auto", 2, 200),
    ("5063DFG", "Pedro Condori", "auto", 2, 60),
    ("6178MNB", "Ana Gutiérrez", "auto", 2, 120),
    ("7284QWE", "Luis Vargas", "auto", 2, 45),
    ("8395ZXC", "Rosa Apaza", "auto", 2, 90),
    ("9406PLK", "Mario Ticona", "moto", 2, 30),
    ("1517VBN", "Elena Rojas", "moto", 2, 25),
    ("2628RTY", "Hugo Limachi", "moto", 2, 1),
    ("3739UIO", "Transportes Illimani", "minibus", 2, 300),
    ("4840ASD", "Sindicato 14 de Septiembre", "minibus", 2, 250),
    ("5951FGH", "Trans. Los Andes", "bus", 2, 500),
    ("6062JKL", "Flota Copacabana", "bus", 2, 400),
    ("7173ZAQ", "Constructora Bolivia", "camion", 2, 600),
    ("8284XSW", "Distribuidora El Alto", "camion", 3, 450),
    ("9395CDE", "Transportes Oriente", "camion", 3, 20),
    ("1406VFR", "Agroindustrial Sur", "camion", 4, 800),
    ("2517BGT", "Minera San José", "camion", 5, 900),
]


class Command(BaseCommand):
    help = "Carga admin (docente), casetas, tarifas y 20 vehículos de prueba (idempotente)."

    def handle(self, *args, **opts):
        # Usuarios autorizados (lista blanca)
        admins = [settings.ADMIN_EMAIL, *settings.EXTRA_ADMIN_EMAILS]
        for email in filter(None, admins):
            u, nuevo = Usuario.objects.get_or_create(
                email_google=email.lower(), defaults={"rol": Usuario.ROL_ADMIN, "nombre": "Administrador"})
            if not nuevo and (u.rol != Usuario.ROL_ADMIN or not u.activo):
                u.rol, u.activo = Usuario.ROL_ADMIN, True
                u.save()
        for email in settings.OPERADOR_EMAILS:
            Usuario.objects.get_or_create(email_google=email.lower(), defaults={"rol": Usuario.ROL_OPERADOR})

        for nombre, ubic in CASETAS:
            Caseta.objects.get_or_create(nombre=nombre, defaults={"ubicacion": ubic})
        for cat, ejes, monto in TARIFAS:
            Tarifa.objects.get_or_create(categoria=cat, ejes=ejes, defaults={"monto": Decimal(monto)})
        for placa, prop, cat, ejes, saldo in VEHICULOS:
            Vehiculo.objects.get_or_create(
                placa=placa,
                defaults={"propietario": prop, "categoria": cat, "ejes": ejes, "saldo": Decimal(saldo)})

        self.stdout.write(self.style.SUCCESS(
            f"Seed OK: {Usuario.objects.count()} usuarios, {Caseta.objects.count()} casetas, "
            f"{Tarifa.objects.count()} tarifas, {Vehiculo.objects.count()} vehículos."))
