from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from apps.common.models import TimeStampedModel


class Service(TimeStampedModel):
    class Category(models.TextChoices):
        LAUNDRY = "laundry", "Lavanderia"
        WASH = "wash", "Lavado"
        DRY = "dry", "Secado"
        IRONING = "ironing", "Planchado"
        SPECIAL = "special", "Especial"

    class PricingMode(models.TextChoices):
        KILO = "kilo", "Por kilo"
        PIEZA = "pieza", "Por pieza"
        FIJO = "fijo", "Precio fijo"

    code = models.CharField(max_length=30, unique=True)
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    category = models.CharField(max_length=20, choices=Category.choices, default=Category.LAUNDRY)
    pricing_mode = models.CharField(max_length=10, choices=PricingMode.choices)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    estimated_turnaround_hours = models.PositiveIntegerField(
        default=24,
        validators=[MinValueValidator(1), MaxValueValidator(240)],
        help_text="Tiempo estimado de entrega en horas.",
    )
    default_iva_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=16.00,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return f"{self.name} ({self.code})"
