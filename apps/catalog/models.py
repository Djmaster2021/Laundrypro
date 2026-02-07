from decimal import Decimal

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone

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

    def effective_unit_price(self):
        active_promotions = self.promotions.filter(
            is_active=True,
            starts_at__lte=timezone.now(),
            ends_at__gte=timezone.now(),
        )
        best_price = Decimal(self.unit_price)
        best_promo = None

        for promo in active_promotions:
            candidate = promo.discounted_price(best_price)
            if candidate < best_price:
                best_price = candidate
                best_promo = promo

        return best_price.quantize(Decimal("0.01")), best_promo


class ServicePriceHistory(models.Model):
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name="price_history")
    previous_price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    new_price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="service_price_changes",
    )
    changed_at = models.DateTimeField(default=timezone.now)
    reason = models.CharField(max_length=180, blank=True)

    class Meta:
        ordering = ["-changed_at"]
        indexes = [models.Index(fields=["service", "-changed_at"])]

    def __str__(self) -> str:
        return f"{self.service.code}: {self.previous_price} -> {self.new_price}"


class ServicePromotion(TimeStampedModel):
    class DiscountType(models.TextChoices):
        PERCENT = "percent", "Porcentaje"
        FIXED = "fixed", "Monto fijo"

    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name="promotions")
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    discount_type = models.CharField(max_length=10, choices=DiscountType.choices, default=DiscountType.PERCENT)
    discount_value = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))])
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="service_promotions_created",
    )

    class Meta:
        ordering = ["-starts_at", "-created_at"]
        indexes = [models.Index(fields=["service", "starts_at", "ends_at", "is_active"])]

    def __str__(self) -> str:
        return f"{self.service.code}: {self.name}"

    def clean(self):
        if self.ends_at <= self.starts_at:
            from django.core.exceptions import ValidationError

            raise ValidationError("La fecha de fin debe ser mayor a la fecha de inicio.")

        if self.discount_type == self.DiscountType.PERCENT and self.discount_value > Decimal("100.00"):
            from django.core.exceptions import ValidationError

            raise ValidationError("El descuento porcentual no puede ser mayor a 100%.")

    def discounted_price(self, base_price):
        base = Decimal(base_price)
        if self.discount_type == self.DiscountType.PERCENT:
            result = base - (base * (Decimal(self.discount_value) / Decimal("100")))
        else:
            result = base - Decimal(self.discount_value)
        return max(result, Decimal("0.00"))

    @property
    def is_current(self):
        now = timezone.now()
        return self.is_active and self.starts_at <= now <= self.ends_at
