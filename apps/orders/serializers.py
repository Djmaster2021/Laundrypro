from django.db import transaction
from rest_framework import serializers

from .models import Order, OrderItem


class OrderItemSerializer(serializers.ModelSerializer):
    service_name = serializers.CharField(source="service.name", read_only=True)
    service_category = serializers.CharField(source="service.category", read_only=True)

    class Meta:
        model = OrderItem
        fields = [
            "id",
            "service",
            "service_name",
            "service_category",
            "description",
            "pricing_mode",
            "quantity",
            "unit_price",
            "iva_rate",
            "subtotal",
            "iva_amount",
            "total",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "service_name", "service_category", "subtotal", "iva_amount", "total", "created_at", "updated_at"]


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, required=False)
    customer_name = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            "id",
            "folio",
            "customer",
            "customer_name",
            "status",
            "currency",
            "wash_status",
            "dry_status",
            "ironing_status",
            "received_at",
            "promised_at",
            "delivered_at",
            "notes",
            "subtotal",
            "iva_amount",
            "total",
            "paid_amount",
            "balance",
            "items",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "folio",
            "subtotal",
            "iva_amount",
            "total",
            "paid_amount",
            "balance",
            "created_at",
            "updated_at",
        ]

    def _create_item(self, order, item_data):
        service = item_data["service"]
        item_data.setdefault("pricing_mode", service.pricing_mode)
        item_data.setdefault("unit_price", service.unit_price)
        item_data.setdefault("iva_rate", service.default_iva_rate)
        return OrderItem.objects.create(order=order, **item_data)

    @transaction.atomic
    def create(self, validated_data):
        items_data = validated_data.pop("items", [])
        order = Order.objects.create(**validated_data)
        for item_data in items_data:
            self._create_item(order, item_data)
        order.refresh_financials(persist=True)
        return order

    @transaction.atomic
    def update(self, instance, validated_data):
        items_data = validated_data.pop("items", None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if items_data is not None:
            instance.items.all().delete()
            for item_data in items_data:
                self._create_item(instance, item_data)

        instance.refresh_financials(persist=True)
        return instance

    def validate_items(self, value):
        if self.instance is None and not value:
            raise serializers.ValidationError("La orden debe incluir al menos un item.")
        return value

    def validate(self, attrs):
        status = attrs.get("status")
        if self.instance and status == Order.Status.DELIVERED and self.instance.balance > 0:
            raise serializers.ValidationError({"status": "No se puede entregar una orden con saldo pendiente."})
        return attrs

    def get_customer_name(self, obj):
        if not obj.customer:
            return ""
        return str(obj.customer)
