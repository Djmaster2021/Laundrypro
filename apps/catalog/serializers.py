from rest_framework import serializers

from .models import Service, ServicePriceHistory, ServicePromotion


class ServiceSerializer(serializers.ModelSerializer):
    effective_unit_price = serializers.SerializerMethodField()
    active_promotion = serializers.SerializerMethodField()

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
            "effective_unit_price",
            "active_promotion",
            "estimated_turnaround_hours",
            "default_iva_rate",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def get_effective_unit_price(self, obj):
        effective, _ = obj.effective_unit_price()
        return str(effective)

    def get_active_promotion(self, obj):
        _, promo = obj.effective_unit_price()
        if promo is None:
            return None
        return {
            "id": promo.id,
            "name": promo.name,
            "discount_type": promo.discount_type,
            "discount_value": str(promo.discount_value),
            "starts_at": promo.starts_at,
            "ends_at": promo.ends_at,
        }


class ServicePriceHistorySerializer(serializers.ModelSerializer):
    service_code = serializers.CharField(source="service.code", read_only=True)
    service_name = serializers.CharField(source="service.name", read_only=True)
    changed_by_username = serializers.CharField(source="changed_by.username", read_only=True)

    class Meta:
        model = ServicePriceHistory
        fields = [
            "id",
            "service",
            "service_code",
            "service_name",
            "previous_price",
            "new_price",
            "reason",
            "changed_by",
            "changed_by_username",
            "changed_at",
        ]
        read_only_fields = fields


class ServicePromotionSerializer(serializers.ModelSerializer):
    service_code = serializers.CharField(source="service.code", read_only=True)
    created_by_username = serializers.CharField(source="created_by.username", read_only=True)
    is_current = serializers.BooleanField(read_only=True)

    class Meta:
        model = ServicePromotion
        fields = [
            "id",
            "service",
            "service_code",
            "name",
            "description",
            "discount_type",
            "discount_value",
            "starts_at",
            "ends_at",
            "is_active",
            "is_current",
            "created_by",
            "created_by_username",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "service_code", "created_by", "created_by_username", "is_current", "created_at", "updated_at"]

    def create(self, validated_data):
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            validated_data["created_by"] = request.user
        return super().create(validated_data)

    def validate(self, attrs):
        starts_at = attrs.get("starts_at", getattr(self.instance, "starts_at", None))
        ends_at = attrs.get("ends_at", getattr(self.instance, "ends_at", None))
        discount_type = attrs.get("discount_type", getattr(self.instance, "discount_type", None))
        discount_value = attrs.get("discount_value", getattr(self.instance, "discount_value", None))

        if starts_at and ends_at and ends_at <= starts_at:
            raise serializers.ValidationError({"ends_at": "La fecha final debe ser mayor a la fecha inicial."})
        if discount_type == ServicePromotion.DiscountType.PERCENT and discount_value and discount_value > 100:
            raise serializers.ValidationError({"discount_value": "El porcentaje no puede ser mayor a 100."})
        return attrs
