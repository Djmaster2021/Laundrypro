from django.urls import path

from .views import InventoryDashboardView

urlpatterns = [
    path("", InventoryDashboardView.as_view(), name="inventory-dashboard"),
]
