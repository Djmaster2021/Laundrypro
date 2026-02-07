from rest_framework import serializers

from .models import CashMovement, CashSession, Payment


class CashSessionSerializer(serializers.ModelSerializer):
    user_username = serializers.CharField(source="user.username", read_only=True)
    is_open = serializers.BooleanField(read_only=True)
    summary = serializers.SerializerMethodField()

    class Meta:
        model = CashSession
        fields = [
            "id",
            "user",
            "user_username",
            "shift",
            "opened_at",
            "opening_amount",
            "closed_at",
            "closing_amount",
            "notes",
            "is_open",
            "summary",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "user_username", "is_open", "summary", "created_at", "updated_at"]

    def get_summary(self, obj):
        return obj.summary()


class CashMovementSerializer(serializers.ModelSerializer):
    created_by_username = serializers.CharField(source="created_by.username", read_only=True)

    class Meta:
        model = CashMovement
        fields = [
            "id",
            "cash_session",
            "movement_type",
            "amount",
            "concept",
            "notes",
            "occurred_at",
            "created_by",
            "created_by_username",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_by", "created_by_username", "created_at", "updated_at"]


class PaymentSerializer(serializers.ModelSerializer):
    order_folio = serializers.CharField(source="order.folio", read_only=True)
    cash_session_info = serializers.SerializerMethodField()
    captured_by_username = serializers.CharField(source="captured_by.username", read_only=True)

    class Meta:
        model = Payment
        fields = [
            "id",
            "order",
            "order_folio",
            "cash_session",
            "cash_session_info",
            "captured_by",
            "captured_by_username",
            "method",
            "status",
            "amount",
            "paid_at",
            "reference",
            "notes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "order_folio",
            "cash_session_info",
            "captured_by",
            "captured_by_username",
            "created_at",
            "updated_at",
        ]

    def get_cash_session_info(self, obj):
        if not obj.cash_session:
            return None
        return {
            "id": obj.cash_session.id,
            "shift": obj.cash_session.shift,
            "opened_at": obj.cash_session.opened_at,
        }

    def create(self, validated_data):
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            validated_data["captured_by"] = request.user
        return super().create(validated_data)
