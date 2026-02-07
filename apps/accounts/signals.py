from django.contrib.auth import get_user_model
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone

from .models import UserCredentialPolicy


@receiver(post_save, sender=get_user_model())
def ensure_user_credential_policy(sender, instance, created, **kwargs):
    if created:
        UserCredentialPolicy.objects.get_or_create(user=instance)


@receiver(pre_save, sender=get_user_model())
def track_password_rotation(sender, instance, **kwargs):
    if not instance.pk:
        return

    previous = sender.objects.filter(pk=instance.pk).only("password").first()
    if not previous or previous.password == instance.password:
        return

    policy, _ = UserCredentialPolicy.objects.get_or_create(user=instance)
    policy.password_changed_at = timezone.now()
    policy.require_password_change = False
    policy.save(update_fields=["password_changed_at", "require_password_change", "updated_at"])
