from django.contrib import admin

from .models import Service, ServicePriceHistory, ServicePromotion


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


@admin.register(ServicePriceHistory)
class ServicePriceHistoryAdmin(admin.ModelAdmin):
    list_display = ("changed_at", "service", "previous_price", "new_price", "changed_by")
    list_filter = ("changed_at",)
    search_fields = ("service__code", "service__name", "changed_by__username")


@admin.register(ServicePromotion)
class ServicePromotionAdmin(admin.ModelAdmin):
    list_display = ("name", "service", "discount_type", "discount_value", "starts_at", "ends_at", "is_active")
    list_filter = ("discount_type", "is_active")
    search_fields = ("name", "service__code", "service__name")
