from django.contrib import admin

from .models import Order, OrderItem


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 1


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        "folio",
        "customer",
        "status",
        "wash_status",
        "dry_status",
        "ironing_status",
        "currency",
        "total",
        "paid_amount",
        "balance",
        "received_at",
    )
    list_filter = ("status", "wash_status", "dry_status", "ironing_status", "currency")
    search_fields = ("folio", "customer__first_name", "customer__last_name", "customer__phone")
    readonly_fields = ("subtotal", "iva_amount", "total", "paid_amount", "balance", "created_at", "updated_at")
    inlines = (OrderItemInline,)


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ("order", "service", "pricing_mode", "quantity", "unit_price", "iva_rate", "total")
    list_filter = ("pricing_mode", "service")
    search_fields = ("order__folio", "service__name")
