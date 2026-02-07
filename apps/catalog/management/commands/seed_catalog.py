from decimal import Decimal

from django.core.management.base import BaseCommand

from apps.catalog.models import Service


SERVICES = [
    {
        "code": "LAV-BAS-KG",
        "name": "Lavado basico",
        "description": "Lavado y secado estandar por kilo.",
        "category": Service.Category.WASH,
        "pricing_mode": Service.PricingMode.KILO,
        "unit_price": Decimal("20.00"),
        "estimated_turnaround_hours": 24,
    },
    {
        "code": "LAV-EXP-KG",
        "name": "Lavado expres",
        "description": "Lavado por kilo con prioridad en cola.",
        "category": Service.Category.WASH,
        "pricing_mode": Service.PricingMode.KILO,
        "unit_price": Decimal("32.00"),
        "estimated_turnaround_hours": 4,
    },
    {
        "code": "LAV-PRE-KG",
        "name": "Lavado premium",
        "description": "Lavado por kilo con suavizante especial y secado delicado.",
        "category": Service.Category.WASH,
        "pricing_mode": Service.PricingMode.KILO,
        "unit_price": Decimal("28.00"),
        "estimated_turnaround_hours": 24,
    },
    {
        "code": "SEC-KG",
        "name": "Solo secado",
        "description": "Secado por kilo sin lavado.",
        "category": Service.Category.DRY,
        "pricing_mode": Service.PricingMode.KILO,
        "unit_price": Decimal("14.00"),
        "estimated_turnaround_hours": 2,
    },
    {
        "code": "ESP-EDR-KG",
        "name": "Edredon por kilo especial",
        "description": "Lavado de edredon por kilo con manejo especial.",
        "category": Service.Category.SPECIAL,
        "pricing_mode": Service.PricingMode.KILO,
        "unit_price": Decimal("35.00"),
        "estimated_turnaround_hours": 48,
    },
    {
        "code": "PLAN-CAM",
        "name": "Planchado camisa",
        "description": "Planchado por pieza.",
        "category": Service.Category.IRONING,
        "pricing_mode": Service.PricingMode.PIEZA,
        "unit_price": Decimal("20.00"),
        "estimated_turnaround_hours": 24,
    },
    {
        "code": "PLAN-PANT",
        "name": "Planchado pantalon",
        "description": "Planchado por pieza.",
        "category": Service.Category.IRONING,
        "pricing_mode": Service.PricingMode.PIEZA,
        "unit_price": Decimal("25.00"),
        "estimated_turnaround_hours": 24,
    },
    {
        "code": "PLAN-BLU",
        "name": "Planchado blusa",
        "description": "Planchado por pieza.",
        "category": Service.Category.IRONING,
        "pricing_mode": Service.PricingMode.PIEZA,
        "unit_price": Decimal("20.00"),
        "estimated_turnaround_hours": 24,
    },
    {
        "code": "PLAN-VEST",
        "name": "Planchado vestido",
        "description": "Planchado por pieza.",
        "category": Service.Category.IRONING,
        "pricing_mode": Service.PricingMode.PIEZA,
        "unit_price": Decimal("45.00"),
        "estimated_turnaround_hours": 24,
    },
    {
        "code": "PLAN-SACO",
        "name": "Planchado saco",
        "description": "Planchado por pieza.",
        "category": Service.Category.IRONING,
        "pricing_mode": Service.PricingMode.PIEZA,
        "unit_price": Decimal("45.00"),
        "estimated_turnaround_hours": 24,
    },
    {
        "code": "PLAN-SAB",
        "name": "Planchado sabanas",
        "description": "Planchado por pieza.",
        "category": Service.Category.IRONING,
        "pricing_mode": Service.PricingMode.PIEZA,
        "unit_price": Decimal("18.00"),
        "estimated_turnaround_hours": 24,
    },
    {
        "code": "PLAN-FUN",
        "name": "Planchado funda",
        "description": "Planchado por pieza.",
        "category": Service.Category.IRONING,
        "pricing_mode": Service.PricingMode.PIEZA,
        "unit_price": Decimal("12.00"),
        "estimated_turnaround_hours": 24,
    },
    {
        "code": "ESP-COB",
        "name": "Cobija especial",
        "description": "Lavado especial por pieza.",
        "category": Service.Category.SPECIAL,
        "pricing_mode": Service.PricingMode.PIEZA,
        "unit_price": Decimal("90.00"),
        "estimated_turnaround_hours": 48,
    },
    {
        "code": "ESP-EDI",
        "name": "Edredon individual",
        "description": "Lavado especial por pieza.",
        "category": Service.Category.SPECIAL,
        "pricing_mode": Service.PricingMode.PIEZA,
        "unit_price": Decimal("150.00"),
        "estimated_turnaround_hours": 48,
    },
    {
        "code": "ESP-EDM",
        "name": "Edredon matrimonial",
        "description": "Lavado especial por pieza.",
        "category": Service.Category.SPECIAL,
        "pricing_mode": Service.PricingMode.PIEZA,
        "unit_price": Decimal("220.00"),
        "estimated_turnaround_hours": 48,
    },
    {
        "code": "ESP-CHM",
        "name": "Chamarra especial",
        "description": "Lavado especial por pieza.",
        "category": Service.Category.SPECIAL,
        "pricing_mode": Service.PricingMode.PIEZA,
        "unit_price": Decimal("120.00"),
        "estimated_turnaround_hours": 48,
    },
]


class Command(BaseCommand):
    help = "Crea o actualiza servicios base para operar el punto de venta."

    def handle(self, *args, **options):
        for service_data in SERVICES:
            service, created = Service.objects.update_or_create(
                code=service_data["code"],
                defaults={
                    "name": service_data["name"],
                    "description": service_data["description"],
                    "category": service_data["category"],
                    "pricing_mode": service_data["pricing_mode"],
                    "unit_price": service_data["unit_price"],
                    "estimated_turnaround_hours": service_data["estimated_turnaround_hours"],
                    "default_iva_rate": Decimal("16.00"),
                    "is_active": True,
                },
            )
            state = "creado" if created else "actualizado"
            self.stdout.write(self.style.SUCCESS(f"Servicio {state}: {service.code} - {service.name}"))

        # Limpieza de codigos legacy reemplazados por este catalogo.
        legacy_codes = ["LAV-KG", "LAV-EDR"]
        deactivated = Service.objects.filter(code__in=legacy_codes, is_active=True).update(is_active=False)
        if deactivated:
            self.stdout.write(self.style.WARNING(f"Servicios legacy desactivados: {deactivated}"))

        self.stdout.write(self.style.SUCCESS("Catalogo base de servicios listo."))
