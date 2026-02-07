from rest_framework import filters, viewsets
from apps.common.throttling import APISensitiveUserRateThrottle

from apps.accounts.api_permissions import IsOwnerOrManagerAdmin, StrictDjangoModelPermissions
from apps.accounts.permissions import ROLE_ADMIN, ROLE_MANAGER, user_has_any_role

from .models import CashMovement, CashSession, Payment
from .serializers import CashMovementSerializer, CashSessionSerializer, PaymentSerializer


class CashSessionViewSet(viewsets.ModelViewSet):
    queryset = CashSession.objects.select_related("user")
    serializer_class = CashSessionSerializer
    permission_classes = [StrictDjangoModelPermissions, IsOwnerOrManagerAdmin]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["user__username", "user__first_name", "user__last_name"]
    ordering_fields = ["opened_at", "closed_at", "created_at"]
    ordering = ["-opened_at"]

    def get_queryset(self):
        qs = super().get_queryset()
        if user_has_any_role(self.request.user, [ROLE_ADMIN, ROLE_MANAGER]):
            return qs
        return qs.filter(user=self.request.user)

    def get_throttles(self):
        if self.request.method in {"POST", "PUT", "PATCH", "DELETE"}:
            return [APISensitiveUserRateThrottle()]
        return super().get_throttles()


class CashMovementViewSet(viewsets.ModelViewSet):
    queryset = CashMovement.objects.select_related("cash_session", "created_by")
    serializer_class = CashMovementSerializer
    permission_classes = [StrictDjangoModelPermissions, IsOwnerOrManagerAdmin]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["concept", "notes", "cash_session__user__username"]
    ordering_fields = ["occurred_at", "amount", "created_at"]
    ordering = ["-occurred_at"]

    def get_queryset(self):
        qs = super().get_queryset()
        if user_has_any_role(self.request.user, [ROLE_ADMIN, ROLE_MANAGER]):
            return qs
        return qs.filter(cash_session__user=self.request.user)

    def get_throttles(self):
        if self.request.method in {"POST", "PUT", "PATCH", "DELETE"}:
            return [APISensitiveUserRateThrottle()]
        return super().get_throttles()

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class PaymentViewSet(viewsets.ModelViewSet):
    queryset = Payment.objects.select_related("order", "cash_session", "captured_by")
    serializer_class = PaymentSerializer
    permission_classes = [StrictDjangoModelPermissions, IsOwnerOrManagerAdmin]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["order__folio", "reference"]
    ordering_fields = ["paid_at", "amount", "created_at"]
    ordering = ["-paid_at"]

    def get_queryset(self):
        qs = super().get_queryset()
        if user_has_any_role(self.request.user, [ROLE_ADMIN, ROLE_MANAGER]):
            return qs
        return qs.filter(captured_by=self.request.user)

    def get_throttles(self):
        if self.request.method in {"POST", "PUT", "PATCH", "DELETE"}:
            return [APISensitiveUserRateThrottle()]
        return super().get_throttles()
