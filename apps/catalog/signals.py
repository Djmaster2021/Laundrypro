from django.db.models.signals import pre_save
from django.dispatch import receiver

from apps.common.context import get_current_request

from .models import Service, ServicePriceHistory


@receiver(pre_save, sender=Service)
def create_price_history(sender, instance: Service, **kwargs):
    if not instance.pk:
        return

    previous = sender.objects.filter(pk=instance.pk).only("unit_price").first()
    if not previous or previous.unit_price == instance.unit_price:
        return

    request = get_current_request()
    actor = None
    if request is not None and getattr(request, "user", None) and request.user.is_authenticated:
        actor = request.user

    ServicePriceHistory.objects.create(
        service=instance,
        previous_price=previous.unit_price,
        new_price=instance.unit_price,
        changed_by=actor,
    )
