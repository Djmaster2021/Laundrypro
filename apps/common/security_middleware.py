from django.conf import settings
from django.contrib.auth import logout
from django.http import JsonResponse
from django.shortcuts import redirect
from django.utils import timezone


def _is_exempt_path(path: str) -> bool:
    allowed = {
        settings.LOGIN_URL.rstrip("/"),
        "/logout",
        "/password/change",
        "/password/change/done",
        "/health",
    }
    normalized = path.rstrip("/")
    return normalized in allowed or normalized.startswith("/static") or normalized.startswith("/media")


class SessionInactivityMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated and not _is_exempt_path(request.path):
            now_ts = timezone.now().timestamp()
            last_activity = request.session.get("last_activity_ts")
            inactivity_limit = int(getattr(settings, "SESSION_INACTIVITY_TIMEOUT_SECONDS", 900))

            if last_activity and (now_ts - float(last_activity)) > inactivity_limit:
                logout(request)
                if request.path.startswith("/api/"):
                    return JsonResponse({"detail": "Sesion expirada por inactividad."}, status=401)
                return redirect("login")

            request.session["last_activity_ts"] = now_ts

        return self.get_response(request)


class PasswordRotationMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not request.user.is_authenticated or _is_exempt_path(request.path):
            return self.get_response(request)

        max_age_days = int(getattr(settings, "PASSWORD_MAX_AGE_DAYS", 90))
        policy = getattr(request.user, "credential_policy", None)
        if policy is None:
            return self.get_response(request)

        age_days = (timezone.now() - policy.password_changed_at).days
        if policy.require_password_change or age_days >= max_age_days:
            if request.path.startswith("/api/"):
                return JsonResponse({"detail": "Credenciales expiradas. Cambia tu contrasena."}, status=403)
            return redirect("password-change")

        return self.get_response(request)
