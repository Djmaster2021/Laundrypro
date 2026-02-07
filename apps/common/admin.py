from django.contrib import admin

from .models import AuditLog, OperationalAlert


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("created_at", "action", "target_model", "target_pk", "actor", "ip_address")
    list_filter = ("action", "target_model", "created_at")
    search_fields = ("target_pk", "metadata", "actor__username", "actor__first_name", "actor__last_name")
    readonly_fields = ("created_at",)


@admin.register(OperationalAlert)
class OperationalAlertAdmin(admin.ModelAdmin):
    list_display = ("last_seen_at", "severity", "event_type", "source", "occurrence_count", "resolved_at")
    list_filter = ("severity", "event_type", "resolved_at")
    search_fields = ("source", "message", "metadata")
