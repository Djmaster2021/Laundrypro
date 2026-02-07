from django.db import models

from apps.common.models import TimeStampedModel


class Customer(TimeStampedModel):
    first_name = models.CharField(max_length=120)
    last_name = models.CharField(max_length=120, blank=True)
    phone = models.CharField(max_length=20, unique=True)
    rfc = models.CharField(max_length=13, blank=True)
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["first_name", "last_name"]
        constraints = [
            models.UniqueConstraint(
                fields=["first_name", "last_name"],
                name="uniq_customer_full_name",
            ),
        ]

    def __str__(self) -> str:
        full_name = f"{self.first_name} {self.last_name}".strip()
        return f"{full_name} ({self.phone})"
