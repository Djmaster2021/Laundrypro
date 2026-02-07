from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from apps.catalog.models import Service, ServicePriceHistory, ServicePromotion


class CatalogPremiumTests(TestCase):
    def setUp(self):
        self.service = Service.objects.create(
            code="PREM-01",
            name="Lavado premium",
            category=Service.Category.WASH,
            pricing_mode=Service.PricingMode.KILO,
            unit_price=Decimal("100.00"),
            default_iva_rate=Decimal("16.00"),
        )

    def test_price_history_created_when_price_changes(self):
        self.service.unit_price = Decimal("120.00")
        self.service.save(update_fields=["unit_price", "updated_at"])

        history = ServicePriceHistory.objects.filter(service=self.service).first()
        self.assertIsNotNone(history)
        self.assertEqual(history.previous_price, Decimal("100.00"))
        self.assertEqual(history.new_price, Decimal("120.00"))

    def test_effective_price_uses_active_promotion(self):
        now = timezone.now()
        ServicePromotion.objects.create(
            service=self.service,
            name="Promo 20%",
            discount_type=ServicePromotion.DiscountType.PERCENT,
            discount_value=Decimal("20.00"),
            starts_at=now - timedelta(hours=1),
            ends_at=now + timedelta(hours=2),
            is_active=True,
        )

        effective_price, promo = self.service.effective_unit_price()
        self.assertEqual(effective_price, Decimal("80.00"))
        self.assertIsNotNone(promo)
        self.assertEqual(promo.name, "Promo 20%")

    def test_effective_price_without_promo_returns_base_price(self):
        effective_price, promo = self.service.effective_unit_price()
        self.assertEqual(effective_price, Decimal("100.00"))
        self.assertIsNone(promo)
