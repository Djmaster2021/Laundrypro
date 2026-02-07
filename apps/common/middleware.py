import hashlib

from django.conf import settings
from django.core.cache import cache
from django.http import HttpResponse
from django.utils import timezone

from .context import clear_current_request, set_current_request


class RequestContextMiddleware:
    """
    Stores the current request in thread-local storage so model signals can
    capture actor and source IP for audit events.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        set_current_request(request)
        try:
            return self.get_response(request)
        finally:
            clear_current_request()


class LoginRateLimitMiddleware:
    """
    Basic brute-force protection for web login endpoint.
    Locks attempts temporarily by (ip, username) after repeated failures.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not self._is_login_attempt(request):
            return self.get_response(request)

        username = (request.POST.get("username", "") or "").strip().lower()
        identity = self._build_identity(self._client_ip(request), username)

        lock_key = self._lock_key(identity)
        if cache.get(lock_key):
            response = HttpResponse("Demasiados intentos de acceso. Intenta mas tarde.", status=429)
            response["Retry-After"] = str(self._lock_seconds())
            return response

        response = self.get_response(request)

        login_succeeded = bool(getattr(request, "user", None) and request.user.is_authenticated and response.status_code == 302)
        if login_succeeded:
            cache.delete(self._fail_key(identity))
            cache.delete(lock_key)
            return response

        fail_key = self._fail_key(identity)
        failed_attempts = cache.get(fail_key, 0) + 1
        cache.set(fail_key, failed_attempts, timeout=self._window_seconds())

        if failed_attempts >= self._max_attempts():
            cache.set(lock_key, timezone.now().isoformat(), timeout=self._lock_seconds())
            cache.delete(fail_key)

        return response

    def _is_login_attempt(self, request):
        if not getattr(settings, "LOGIN_RATE_LIMIT_ENABLED", True):
            return False
        login_path = getattr(settings, "LOGIN_URL", "/login/") or "/login/"
        return request.method == "POST" and request.path.rstrip("/") == login_path.rstrip("/")

    def _client_ip(self, request):
        xff = request.META.get("HTTP_X_FORWARDED_FOR")
        if xff:
            return xff.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR", "unknown")

    def _build_identity(self, ip, username):
        raw = f"{ip}|{username}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def _max_attempts(self):
        return int(getattr(settings, "LOGIN_RATE_LIMIT_MAX_ATTEMPTS", 5))

    def _window_seconds(self):
        return int(getattr(settings, "LOGIN_RATE_LIMIT_WINDOW_SECONDS", 900))

    def _lock_seconds(self):
        return int(getattr(settings, "LOGIN_RATE_LIMIT_LOCK_SECONDS", 900))

    def _fail_key(self, identity):
        return f"login:fail:{identity}"

    def _lock_key(self, identity):
        return f"login:lock:{identity}"
