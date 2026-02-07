from rest_framework.routers import DefaultRouter

from .views import ExpenseViewSet, InventoryMovementViewSet, SupplyViewSet

router = DefaultRouter()
router.register("supplies", SupplyViewSet, basename="supply")
router.register("movements", InventoryMovementViewSet, basename="inventory-movement")
router.register("expenses", ExpenseViewSet, basename="expense")

urlpatterns = router.urls
