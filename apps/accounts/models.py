from django.conf import settings
from django.db import models
from django.utils import timezone


class UserCredentialPolicy(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="credential_policy")
    password_changed_at = models.DateTimeField(default=timezone.now)
    require_password_change = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["user_id"]

    def __str__(self) -> str:
        return f"CredentialPolicy<{self.user_id}>"
