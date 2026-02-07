from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q, Sum
from django.utils import timezone

from apps.common.models import TimeStampedModel
from apps.orders.models import Order


class CashSession(TimeStampedModel):
    class Shift(models.TextChoices):
        MORNING = "morning", "Mañana"
        EVENING = "evening", "Tarde"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="cash_sessions")
    shift = models.CharField(max_length=20, choices=Shift.choices)
    opened_at = models.DateTimeField(default=timezone.now)
    opening_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    closed_at = models.DateTimeField(null=True, blank=True)
    closing_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-opened_at", "-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["user"],
                condition=Q(closed_at__isnull=True),
                name="uniq_open_cash_session_per_user",
            )
        ]

    def __str__(self) -> str:
        return f"Caja {self.user} - {self.get_shift_display()} - {self.opened_at:%Y-%m-%d}"

    @property
    def is_open(self) -> bool:
        return self.closed_at is None

    def summary(self):
        payments_qs = self.payments.filter(status=Payment.Status.APPLIED)
        totals = {
            "cash": payments_qs.filter(method=Payment.Method.CASH).aggregate(total=Sum("amount"))["total"] or Decimal("0.00"),
            "card": payments_qs.filter(method=Payment.Method.CARD).aggregate(total=Sum("amount"))["total"] or Decimal("0.00"),
            "transfer": payments_qs.filter(method=Payment.Method.TRANSFER).aggregate(total=Sum("amount"))["total"] or Decimal("0.00"),
            "other": payments_qs.filter(method=Payment.Method.OTHER).aggregate(total=Sum("amount"))["total"] or Decimal("0.00"),
        }
        movement_income = (
            self.movements.filter(movement_type=CashMovement.MovementType.INCOME).aggregate(total=Sum("amount"))["total"]
            or Decimal("0.00")
        )
        totals["income_total"] = sum(totals.values(), Decimal("0.00"))
        totals["movement_income_total"] = movement_income
        totals["expense_total"] = (
            self.movements.filter(movement_type=CashMovement.MovementType.EXPENSE).aggregate(total=Sum("amount"))["total"]
            or Decimal("0.00")
        )
        totals["adjustment_total"] = (
            self.movements.filter(movement_type=CashMovement.MovementType.ADJUSTMENT).aggregate(total=Sum("amount"))["total"]
            or Decimal("0.00")
        )
        totals["generated_total"] = totals["income_total"] + totals["movement_income_total"]
        totals["net_gain"] = totals["generated_total"] - totals["expense_total"]
        totals["expected_cash"] = (
            Decimal(self.opening_amount)
            + totals["cash"]
            + totals["movement_income_total"]
            + totals["adjustment_total"]
            - totals["expense_total"]
        )
        return totals


class CashMovement(TimeStampedModel):
    class MovementType(models.TextChoices):
        INCOME = "income", "Ingreso"
        EXPENSE = "expense", "Egreso"
        ADJUSTMENT = "adjustment", "Ajuste"

    cash_session = models.ForeignKey(CashSession, on_delete=models.CASCADE, related_name="movements")
    movement_type = models.CharField(max_length=20, choices=MovementType.choices)
    amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))])
    concept = models.CharField(max_length=160)
    notes = models.TextField(blank=True)
    occurred_at = models.DateTimeField(default=timezone.now)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="cash_movements",
    )

    class Meta:
        ordering = ["-occurred_at", "-created_at"]

    def __str__(self) -> str:
        return f"{self.cash_session} - {self.get_movement_type_display()} - {self.amount}"


class Payment(TimeStampedModel):
    class Method(models.TextChoices):
        CASH = "cash", "Efectivo"
        CARD = "card", "Tarjeta"
        TRANSFER = "transfer", "Transferencia"
        OTHER = "other", "Otro"

    class Status(models.TextChoices):
        APPLIED = "applied", "Aplicado"
        VOID = "void", "Anulado"

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="payments")
    cash_session = models.ForeignKey(CashSession, on_delete=models.SET_NULL, null=True, blank=True, related_name="payments")
    captured_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="captured_payments",
    )
    method = models.CharField(max_length=20, choices=Method.choices, default=Method.CASH)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.APPLIED)
    amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))])
    paid_at = models.DateTimeField(default=timezone.now)
    reference = models.CharField(max_length=120, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-paid_at", "-created_at"]

    def __str__(self) -> str:
        return f"{self.order.folio} - {self.amount}"

    def save(self, *args, **kwargs):
        if self.captured_by and not self.cash_session:
            self.cash_session = (
                CashSession.objects.filter(user=self.captured_by, closed_at__isnull=True).order_by("-opened_at").first()
            )
        super().save(*args, **kwargs)
        self.order.refresh_financials(persist=True)

    def delete(self, *args, **kwargs):
        order = self.order
        super().delete(*args, **kwargs)
        order.refresh_financials(persist=True)
