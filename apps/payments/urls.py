from rest_framework.routers import DefaultRouter

from .views import CashMovementViewSet, CashSessionViewSet, PaymentViewSet

router = DefaultRouter()
router.register("", PaymentViewSet, basename="payment")
router.register("sessions", CashSessionViewSet, basename="cash-session")
router.register("movements", CashMovementViewSet, basename="cash-movement")

urlpatterns = router.urls
