from rest_framework import serializers

from .models import Expense, InventoryMovement, Supply


class SupplySerializer(serializers.ModelSerializer):
    low_stock = serializers.SerializerMethodField()

    class Meta:
        model = Supply
        fields = [
            "id",
            "code",
            "name",
            "unit",
            "min_stock",
            "current_stock",
            "low_stock",
            "is_active",
            "notes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "low_stock", "created_at", "updated_at"]

    def get_low_stock(self, obj):
        return obj.current_stock <= obj.min_stock


class InventoryMovementSerializer(serializers.ModelSerializer):
    supply_name = serializers.CharField(source="supply.name", read_only=True)
    created_by_username = serializers.CharField(source="created_by.username", read_only=True)

    class Meta:
        model = InventoryMovement
        fields = [
            "id",
            "supply",
            "supply_name",
            "movement_type",
            "quantity",
            "unit_cost",
            "concept",
            "notes",
            "occurred_at",
            "created_by",
            "created_by_username",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "occurred_at", "created_by", "created_by_username", "created_at", "updated_at"]


class ExpenseSerializer(serializers.ModelSerializer):
    created_by_username = serializers.CharField(source="created_by.username", read_only=True)
    related_supply_name = serializers.CharField(source="related_supply.name", read_only=True)

    class Meta:
        model = Expense
        fields = [
            "id",
            "category",
            "amount",
            "description",
            "expense_date",
            "related_supply",
            "related_supply_name",
            "created_by",
            "created_by_username",
            "notes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_by", "created_by_username", "related_supply_name", "created_at", "updated_at"]
