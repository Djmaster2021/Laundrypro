from rest_framework import filters, viewsets

from apps.accounts.api_permissions import StrictDjangoModelPermissions

from .models import Customer
from .serializers import CustomerSerializer


class CustomerViewSet(viewsets.ModelViewSet):
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer
    permission_classes = [StrictDjangoModelPermissions]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["first_name", "last_name", "phone", "rfc"]
    ordering_fields = ["first_name", "created_at"]
    ordering = ["first_name", "last_name"]
