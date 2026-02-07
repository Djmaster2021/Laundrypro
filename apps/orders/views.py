from rest_framework import filters, viewsets

from apps.accounts.api_permissions import StrictDjangoModelPermissions

from .models import Order, OrderItem
from .serializers import OrderItemSerializer, OrderSerializer


class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.select_related("customer").prefetch_related("items", "payments")
    serializer_class = OrderSerializer
    permission_classes = [StrictDjangoModelPermissions]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["folio", "customer__first_name", "customer__last_name", "customer__phone"]
    ordering_fields = ["created_at", "received_at", "total", "balance"]
    ordering = ["-created_at"]


class OrderItemViewSet(viewsets.ModelViewSet):
    queryset = OrderItem.objects.select_related("order", "service")
    serializer_class = OrderItemSerializer
    permission_classes = [StrictDjangoModelPermissions]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["order__folio", "service__name", "description"]
    ordering_fields = ["created_at", "total"]
    ordering = ["created_at"]
