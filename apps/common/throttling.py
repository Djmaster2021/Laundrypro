from rest_framework.throttling import AnonRateThrottle, UserRateThrottle
from django.conf import settings


class APIAnonIPRateThrottle(AnonRateThrottle):
    scope = "api_anon_ip"


class APIUserRateThrottle(UserRateThrottle):
    scope = "api_user"


class APISensitiveUserRateThrottle(UserRateThrottle):
    scope = "api_sensitive_user"

    def get_rate(self):
        return getattr(settings, "API_THROTTLE_SENSITIVE_USER_RATE", "60/min")
