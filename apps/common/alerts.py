from __future__ import annotations

import hashlib
import logging

from django.utils import timezone

from .models import OperationalAlert

logger = logging.getLogger("security")


def _fingerprint(event_type: str, source: str, message: str) -> str:
    return hashlib.sha256(f"{event_type}|{source}|{message}".encode("utf-8")).hexdigest()


def raise_operational_alert(*, event_type: str, source: str, severity: str, message: str, metadata: dict | None = None):
    fingerprint = _fingerprint(event_type, source, message)
    now = timezone.now()

    alert = (
        OperationalAlert.objects.filter(fingerprint=fingerprint, resolved_at__isnull=True)
        .order_by("-last_seen_at")
        .first()
    )

    if alert:
        alert.last_seen_at = now
        alert.occurrence_count += 1
        if metadata:
            merged = alert.metadata.copy()
            merged.update(metadata)
            alert.metadata = merged
        alert.save(update_fields=["last_seen_at", "occurrence_count", "metadata"])
        return alert

    return OperationalAlert.objects.create(
        event_type=event_type,
        source=source,
        severity=severity,
        message=message,
        metadata=metadata or {},
        fingerprint=fingerprint,
        first_seen_at=now,
        last_seen_at=now,
    )


def emit_db_down_alert(exc: Exception):
    logger.critical(
        "db_unavailable",
        extra={
            "path": "/health/",
            "method": "GET",
            "status_code": 503,
            "reason": exc.__class__.__name__,
            "ip": "",
            "user_id": None,
        },
    )

    # Best effort: if DB is intermittently available, persist alert.
    try:
        raise_operational_alert(
            event_type="database.unavailable",
            source="healthcheck",
            severity=OperationalAlert.Severity.CRITICAL,
            message="Healthcheck detecto base de datos no disponible.",
            metadata={"error_type": exc.__class__.__name__},
        )
    except Exception:
        pass
