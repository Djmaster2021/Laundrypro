from django.contrib import admin

from .models import CashMovement, CashSession, Payment


@admin.register(CashSession)
class CashSessionAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "shift", "opened_at", "closed_at", "opening_amount", "closing_amount")
    list_filter = ("shift", "closed_at")
    search_fields = ("user__username", "user__first_name", "user__last_name")


@admin.register(CashMovement)
class CashMovementAdmin(admin.ModelAdmin):
    list_display = ("cash_session", "movement_type", "amount", "concept", "occurred_at", "created_by")
    list_filter = ("movement_type",)
    search_fields = ("concept", "notes", "cash_session__user__username")


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("order", "cash_session", "captured_by", "method", "status", "amount", "paid_at")
    list_filter = ("method", "status")
    search_fields = ("order__folio", "reference")
