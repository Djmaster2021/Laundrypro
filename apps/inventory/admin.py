from django.contrib import admin

from .models import Expense, InventoryMovement, Supply


@admin.register(Supply)
class SupplyAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "unit", "current_stock", "min_stock", "is_active")
    list_filter = ("unit", "is_active")
    search_fields = ("code", "name")


@admin.register(InventoryMovement)
class InventoryMovementAdmin(admin.ModelAdmin):
    list_display = ("supply", "movement_type", "quantity", "unit_cost", "concept", "occurred_at", "created_by")
    list_filter = ("movement_type",)
    search_fields = ("supply__name", "concept", "notes")


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ("category", "amount", "expense_date", "related_supply", "created_by")
    list_filter = ("category",)
    search_fields = ("description", "notes", "related_supply__name")
