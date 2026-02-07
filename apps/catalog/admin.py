from django.contrib import admin

from .models import Service


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = (
        "code",
        "name",
        "category",
        "pricing_mode",
        "unit_price",
        "estimated_turnaround_hours",
        "default_iva_rate",
        "is_active",
    )
    list_filter = ("category", "pricing_mode", "is_active")
    search_fields = ("code", "name")
