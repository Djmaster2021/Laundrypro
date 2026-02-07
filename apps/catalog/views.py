from rest_framework import filters, viewsets

from apps.accounts.api_permissions import StrictDjangoModelPermissions

from .models import Service, ServicePriceHistory, ServicePromotion
from .serializers import ServicePriceHistorySerializer, ServicePromotionSerializer, ServiceSerializer


class ServiceViewSet(viewsets.ModelViewSet):
    queryset = Service.objects.all()
    serializer_class = ServiceSerializer
    permission_classes = [StrictDjangoModelPermissions]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["code", "name"]
    ordering_fields = ["name", "unit_price", "created_at"]
    ordering = ["name"]

    def get_queryset(self):
        queryset = super().get_queryset()
        category = self.request.query_params.get("category")
        if category:
            queryset = queryset.filter(category=category)
        return queryset


class ServicePriceHistoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ServicePriceHistory.objects.select_related("service", "changed_by")
    serializer_class = ServicePriceHistorySerializer
    permission_classes = [StrictDjangoModelPermissions]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["service__code", "service__name", "changed_by__username"]
    ordering_fields = ["changed_at", "new_price", "previous_price"]
    ordering = ["-changed_at"]


class ServicePromotionViewSet(viewsets.ModelViewSet):
    queryset = ServicePromotion.objects.select_related("service", "created_by")
    serializer_class = ServicePromotionSerializer
    permission_classes = [StrictDjangoModelPermissions]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name", "service__code", "service__name"]
    ordering_fields = ["starts_at", "ends_at", "discount_value", "created_at"]
    ordering = ["-starts_at"]

    def get_queryset(self):
        queryset = super().get_queryset()
        only_current = self.request.query_params.get("current")
        if only_current in {"1", "true", "yes"}:
            from django.utils import timezone

            now = timezone.now()
            queryset = queryset.filter(is_active=True, starts_at__lte=now, ends_at__gte=now)
        return queryset
