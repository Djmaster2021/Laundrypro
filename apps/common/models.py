from django.conf import settings
from django.db import models


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class AuditLog(models.Model):
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
    )
    action = models.CharField(max_length=80)
    target_model = models.CharField(max_length=100)
    target_pk = models.CharField(max_length=64)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["action", "-created_at"]),
            models.Index(fields=["target_model", "target_pk"]),
        ]

    def __str__(self) -> str:
        return f"{self.action} -> {self.target_model}:{self.target_pk}"


class OperationalAlert(models.Model):
    class Severity(models.TextChoices):
        INFO = "info", "Info"
        WARNING = "warning", "Advertencia"
        CRITICAL = "critical", "Critica"

    event_type = models.CharField(max_length=80)
    source = models.CharField(max_length=160)
    severity = models.CharField(max_length=20, choices=Severity.choices, default=Severity.WARNING)
    message = models.CharField(max_length=255)
    metadata = models.JSONField(default=dict, blank=True)
    fingerprint = models.CharField(max_length=64, db_index=True)
    occurrence_count = models.PositiveIntegerField(default=1)
    first_seen_at = models.DateTimeField()
    last_seen_at = models.DateTimeField()
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-last_seen_at"]
        indexes = [
            models.Index(fields=["event_type", "severity"]),
            models.Index(fields=["resolved_at", "-last_seen_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.severity}:{self.event_type} ({self.source})"
