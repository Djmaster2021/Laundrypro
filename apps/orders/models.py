from decimal import Decimal

from django.core.validators import MaxValueValidator, MinValueValidator
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Sum
from django.utils import timezone

from apps.catalog.models import Service
from apps.common.models import TimeStampedModel
from apps.customers.models import Customer


class Order(TimeStampedModel):
    class Status(models.TextChoices):
        RECEIVED = "received", "Recibida"
        IN_PROCESS = "in_process", "En proceso"
        READY = "ready", "Lista"
        DELIVERED = "delivered", "Entregada"
        CANCELLED = "cancelled", "Cancelada"

    class Currency(models.TextChoices):
        MXN = "MXN", "Peso mexicano"

    class AreaStatus(models.TextChoices):
        PENDING = "pending", "Pendiente"
        IN_PROGRESS = "in_progress", "En proceso"
        DONE = "done", "Completado"
        NOT_APPLICABLE = "na", "No aplica"

    folio = models.CharField(max_length=32, unique=True, blank=True)
    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True, blank=True, related_name="orders")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.RECEIVED)
    currency = models.CharField(max_length=3, choices=Currency.choices, default=Currency.MXN)
    wash_status = models.CharField(max_length=20, choices=AreaStatus.choices, default=AreaStatus.PENDING)
    dry_status = models.CharField(max_length=20, choices=AreaStatus.choices, default=AreaStatus.PENDING)
    ironing_status = models.CharField(max_length=20, choices=AreaStatus.choices, default=AreaStatus.NOT_APPLICABLE)
    received_at = models.DateTimeField(default=timezone.now)
    promised_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)

    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0, editable=False)
    iva_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, editable=False)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0, editable=False)
    paid_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, editable=False)
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0, editable=False)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.folio

    def save(self, *args, **kwargs):
        if not self.folio:
            self.folio = f"ORD-{timezone.now():%Y%m%d%H%M%S%f}"[-32:]
        self._sync_area_statuses()
        self._sync_global_status_from_areas()
        self._validate_business_rules()
        super().save(*args, **kwargs)

    def refresh_financials(self, persist: bool = False):
        self._sync_area_statuses()
        self._sync_global_status_from_areas()
        item_totals = self.items.aggregate(
            subtotal=Sum("subtotal"),
            iva_amount=Sum("iva_amount"),
            total=Sum("total"),
        )
        paid_total = self.payments.filter(status="applied").aggregate(total=Sum("amount"))["total"] or Decimal("0.00")

        self.subtotal = item_totals["subtotal"] or Decimal("0.00")
        self.iva_amount = item_totals["iva_amount"] or Decimal("0.00")
        self.total = item_totals["total"] or Decimal("0.00")
        self.paid_amount = paid_total
        self.balance = self.total - self.paid_amount

        if persist:
            self.save(
                update_fields=[
                    "subtotal",
                    "iva_amount",
                    "total",
                    "paid_amount",
                    "balance",
                    "wash_status",
                    "dry_status",
                    "ironing_status",
                    "updated_at",
                ]
            )

    def _validate_business_rules(self):
        if not self.pk:
            return

        previous = Order.objects.filter(pk=self.pk).only("status", "balance").first()
        if not previous:
            return

        if self.status == self.Status.CANCELLED and previous.status != self.Status.RECEIVED:
            raise ValidationError("Solo se puede cancelar una orden en estado Recibida.")

        if self.status == self.Status.DELIVERED and self.balance > Decimal("0.00"):
            raise ValidationError("No se puede entregar una orden con saldo pendiente.")

    def _sync_area_statuses(self):
        if not self.pk:
            return

        has_ironing_items = self.items.filter(service__category=Service.Category.IRONING).exists()
        if has_ironing_items and self.ironing_status == self.AreaStatus.NOT_APPLICABLE:
            self.ironing_status = self.AreaStatus.PENDING
        elif not has_ironing_items:
            self.ironing_status = self.AreaStatus.NOT_APPLICABLE

    def _sync_global_status_from_areas(self):
        if self.status in (self.Status.DELIVERED, self.Status.CANCELLED):
            return

        required_statuses = [self.wash_status, self.dry_status]
        if self.ironing_status != self.AreaStatus.NOT_APPLICABLE:
            required_statuses.append(self.ironing_status)

        all_done = all(status == self.AreaStatus.DONE for status in required_statuses)
        any_in_progress = any(status == self.AreaStatus.IN_PROGRESS for status in required_statuses)

        if all_done:
            self.status = self.Status.READY
        elif any_in_progress:
            self.status = self.Status.IN_PROCESS
        else:
            self.status = self.Status.RECEIVED


class OrderItem(TimeStampedModel):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    service = models.ForeignKey(Service, on_delete=models.PROTECT, related_name="order_items")
    description = models.CharField(max_length=200, blank=True)
    pricing_mode = models.CharField(max_length=10, choices=Service.PricingMode.choices)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))])
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    iva_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=16.00,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )

    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0, editable=False)
    iva_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, editable=False)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0, editable=False)

    class Meta:
        ordering = ["created_at"]

    def __str__(self) -> str:
        return f"{self.order.folio} - {self.service.name}"

    def save(self, *args, **kwargs):
        if not self.description:
            self.description = self.service.name
        if not self.pricing_mode:
            self.pricing_mode = self.service.pricing_mode
        if not self.unit_price:
            self.unit_price = self.service.unit_price
        if not self.iva_rate:
            self.iva_rate = self.service.default_iva_rate

        base = Decimal(self.quantity) * Decimal(self.unit_price)
        self.subtotal = base.quantize(Decimal("0.01"))
        self.iva_amount = (self.subtotal * (Decimal(self.iva_rate) / Decimal("100"))).quantize(Decimal("0.01"))
        self.total = (self.subtotal + self.iva_amount).quantize(Decimal("0.01"))

        super().save(*args, **kwargs)
        self.order.refresh_financials(persist=True)

    def delete(self, *args, **kwargs):
        order = self.order
        super().delete(*args, **kwargs)
        order.refresh_financials(persist=True)
