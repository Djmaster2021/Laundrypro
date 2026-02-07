from __future__ import annotations

from .alerts import raise_operational_alert
from .models import OperationalAlert


class ServerErrorAlertMiddleware:
    """
    Emits an operational alert for API/web responses returning HTTP 500.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        if response.status_code >= 500:
            try:
                raise_operational_alert(
                    event_type="http.server_error",
                    source=request.path,
                    severity=OperationalAlert.Severity.CRITICAL,
                    message="Se detecto error 500 en la aplicacion.",
                    metadata={"path": request.path, "method": request.method, "status": response.status_code},
                )
            except Exception:
                # Never fail request handling due to alert persistence errors.
                pass

        return response
