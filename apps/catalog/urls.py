from rest_framework.routers import DefaultRouter

from .views import ServicePriceHistoryViewSet, ServicePromotionViewSet, ServiceViewSet

router = DefaultRouter()
router.register("services", ServiceViewSet, basename="service")
router.register("promotions", ServicePromotionViewSet, basename="service-promotion")
router.register("price-history", ServicePriceHistoryViewSet, basename="service-price-history")

urlpatterns = router.urls
