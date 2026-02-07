from rest_framework.routers import DefaultRouter

from .views import OrderItemViewSet, OrderViewSet

router = DefaultRouter()
router.register("", OrderViewSet, basename="order")
router.register("items", OrderItemViewSet, basename="order-item")

urlpatterns = router.urls
