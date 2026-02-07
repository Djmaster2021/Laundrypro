import logging

from rest_framework.exceptions import NotAuthenticated, PermissionDenied, Throttled
from rest_framework.views import exception_handler

security_logger = logging.getLogger("security")


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)
    request = context.get("request")

    if request is not None and isinstance(exc, (NotAuthenticated, PermissionDenied, Throttled)):
        ip = request.META.get("HTTP_X_FORWARDED_FOR", request.META.get("REMOTE_ADDR", "")).split(",")[0].strip()
        user_id = request.user.id if getattr(request, "user", None) and request.user.is_authenticated else None
        security_logger.warning(
            "api_access_denied",
            extra={
                "path": request.path,
                "method": request.method,
                "status_code": response.status_code if response else 500,
                "reason": exc.__class__.__name__,
                "ip": ip,
                "user_id": user_id,
            },
        )

    return response
