from rest_framework import serializers

from .models import Service


class ServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Service
        fields = [
            "id",
            "code",
            "name",
            "description",
            "category",
            "pricing_mode",
            "unit_price",
            "estimated_turnaround_hours",
            "default_iva_rate",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]
