from __future__ import annotations

from typing import Any

from .context import get_current_request
from .models import AuditLog


def _serialize_value(value: Any):
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if hasattr(value, "pk"):
        return value.pk
    return str(value) if not isinstance(value, (int, float, bool, dict, list, tuple, str)) else value


def _serialize_changes(changes: dict[str, tuple[Any, Any]]):
    return {
        field: {
            "before": _serialize_value(before),
            "after": _serialize_value(after),
        }
        for field, (before, after) in changes.items()
    }


def _normalize_json(value: Any):
    if isinstance(value, dict):
        return {str(k): _normalize_json(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_normalize_json(v) for v in value]
    return _serialize_value(value)


def log_audit_event(action: str, obj, *, changes: dict[str, tuple[Any, Any]] | None = None, metadata: dict | None = None):
    request = get_current_request()
    user = None
    ip_address = ""
    if request is not None:
        user = request.user if getattr(request, "user", None) and request.user.is_authenticated else None
        xff = request.META.get("HTTP_X_FORWARDED_FOR")
        ip_address = xff.split(",")[0].strip() if xff else request.META.get("REMOTE_ADDR", "")

    data = _normalize_json(metadata.copy()) if metadata else {}
    if changes:
        data["changes"] = _serialize_changes(changes)

    AuditLog.objects.create(
        actor=user,
        action=action,
        target_model=f"{obj._meta.app_label}.{obj.__class__.__name__}",
        target_pk=str(obj.pk),
        ip_address=ip_address,
        metadata=data,
    )
