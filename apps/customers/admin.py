from django.contrib import admin

from .models import Customer


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ("first_name", "last_name", "phone", "is_active")
    list_filter = ("is_active",)
    search_fields = ("first_name", "last_name", "phone", "rfc")
