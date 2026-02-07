from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models, transaction

from apps.common.models import TimeStampedModel


class Supply(TimeStampedModel):
    class Unit(models.TextChoices):
        LITER = "liter", "Litro"
        KILOGRAM = "kilogram", "Kilogramo"
        PIECE = "piece", "Pieza"
        BOX = "box", "Caja"

    code = models.CharField(max_length=30, unique=True)
    name = models.CharField(max_length=120)
    unit = models.CharField(max_length=20, choices=Unit.choices)
    min_stock = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    current_stock = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return f"{self.name} ({self.code})"


class InventoryMovement(TimeStampedModel):
    class MovementType(models.TextChoices):
        ENTRY = "entry", "Entrada"
        CONSUMPTION = "consumption", "Consumo"
        LOSS = "loss", "Merma"
        ADJUSTMENT_IN = "adjustment_in", "Ajuste +"
        ADJUSTMENT_OUT = "adjustment_out", "Ajuste -"

    supply = models.ForeignKey(Supply, on_delete=models.PROTECT, related_name="movements")
    movement_type = models.CharField(max_length=20, choices=MovementType.choices)
    quantity = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))])
    unit_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    concept = models.CharField(max_length=160)
    notes = models.TextField(blank=True)
    occurred_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="inventory_movements",
    )

    class Meta:
        ordering = ["-occurred_at", "-created_at"]

    def __str__(self) -> str:
        return f"{self.supply.name} - {self.get_movement_type_display()} - {self.quantity}"

    def signed_quantity(self) -> Decimal:
        if self.movement_type in (self.MovementType.ENTRY, self.MovementType.ADJUSTMENT_IN):
            return Decimal(self.quantity)
        return Decimal(self.quantity) * Decimal("-1")

    def save(self, *args, **kwargs):
        with transaction.atomic():
            if self.pk:
                previous = InventoryMovement.objects.select_for_update().get(pk=self.pk)
                previous_supply = previous.supply
                old_delta = previous.signed_quantity()
            else:
                previous = None
                previous_supply = None
                old_delta = Decimal("0.00")

            new_delta = self.signed_quantity()

            if previous and previous_supply is not None:
                if previous_supply.id != self.supply_id:
                    previous_supply.current_stock = Decimal(previous_supply.current_stock) - old_delta
                    if previous_supply.current_stock < 0:
                        raise ValidationError("No se puede actualizar: stock negativo en insumo previo.")
                    previous_supply.save(update_fields=["current_stock", "updated_at"])

                    self.supply.current_stock = Decimal(self.supply.current_stock) + new_delta
                    if self.supply.current_stock < 0:
                        raise ValidationError("Stock insuficiente para este movimiento.")
                    self.supply.save(update_fields=["current_stock", "updated_at"])
                else:
                    diff = new_delta - old_delta
                    self.supply.current_stock = Decimal(self.supply.current_stock) + diff
                    if self.supply.current_stock < 0:
                        raise ValidationError("Stock insuficiente para este movimiento.")
                    self.supply.save(update_fields=["current_stock", "updated_at"])
            else:
                self.supply.current_stock = Decimal(self.supply.current_stock) + new_delta
                if self.supply.current_stock < 0:
                    raise ValidationError("Stock insuficiente para este movimiento.")
                self.supply.save(update_fields=["current_stock", "updated_at"])

            super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        with transaction.atomic():
            delta = self.signed_quantity()
            self.supply.current_stock = Decimal(self.supply.current_stock) - delta
            if self.supply.current_stock < 0:
                raise ValidationError("No se puede eliminar el movimiento: dejaria stock negativo.")
            self.supply.save(update_fields=["current_stock", "updated_at"])
            super().delete(*args, **kwargs)


class Expense(TimeStampedModel):
    class Category(models.TextChoices):
        SUPPLY_PURCHASE = "supply_purchase", "Compra de insumo"
        SERVICES = "services", "Servicios"
        PAYROLL = "payroll", "Nomina"
        OTHER = "other", "Otro"

    category = models.CharField(max_length=30, choices=Category.choices)
    amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))])
    description = models.CharField(max_length=200)
    expense_date = models.DateField()
    related_supply = models.ForeignKey(Supply, on_delete=models.SET_NULL, null=True, blank=True, related_name="expenses")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="expenses_created",
    )
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-expense_date", "-created_at"]

    def __str__(self) -> str:
        return f"{self.get_category_display()} - {self.amount}"
