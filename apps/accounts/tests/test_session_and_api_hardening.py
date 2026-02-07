from decimal import Decimal

from django.contrib.auth.models import Group, User
from django.contrib.auth.password_validation import validate_password
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.utils import timezone

from apps.catalog.models import Service
from apps.customers.models import Customer
from apps.orders.models import Order, OrderItem
from apps.payments.models import Payment


@override_settings(
    API_THROTTLE_SENSITIVE_USER_RATE="2/min",
    SESSION_INACTIVITY_TIMEOUT_SECONDS=60,
)
class SessionAndAPIHardeningTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_roles")

    def setUp(self):
        cache.clear()
        self.customer = Customer.objects.create(first_name="Cliente", last_name="Hardening", phone="5512340000")
        self.service = Service.objects.create(
            code="SEC-01",
            name="Servicio Seguridad",
            category=Service.Category.WASH,
            pricing_mode=Service.PricingMode.KILO,
            unit_price=Decimal("20.00"),
            default_iva_rate=Decimal("16.00"),
        )

        self.seller_1 = User.objects.create_user(username="seller_hard_1", password="StrongPass123!")
        self.seller_2 = User.objects.create_user(username="seller_hard_2", password="StrongPass123!")
        self.seller_1.groups.add(Group.objects.get(name="Vendedora"))
        self.seller_2.groups.add(Group.objects.get(name="Vendedora"))

        self.order = Order.objects.create(customer=self.customer)
        OrderItem.objects.create(
            order=self.order,
            service=self.service,
            pricing_mode=self.service.pricing_mode,
            quantity=Decimal("1.00"),
            unit_price=self.service.unit_price,
            iva_rate=self.service.default_iva_rate,
        )
        self.order.refresh_financials(persist=True)

    def test_password_complexity_validator_rejects_weak_password(self):
        with self.assertRaises(ValidationError):
            validate_password("password123")

    def test_session_expires_by_inactivity(self):
        self.client.force_login(self.seller_1)
        session = self.client.session
        session["last_activity_ts"] = timezone.now().timestamp() - 120
        session.save()

        response = self.client.get("/pos/")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/login/")

    def test_seller_cannot_access_other_seller_payment(self):
        payment = Payment.objects.create(
            order=self.order,
            captured_by=self.seller_1,
            method=Payment.Method.CASH,
            amount=Decimal("10.00"),
        )

        self.client.force_login(self.seller_2)
        response = self.client.get(f"/api/payments/{payment.id}/")
        self.assertEqual(response.status_code, 404)

    def test_sensitive_throttle_limits_payment_writes(self):
        self.client.force_login(self.seller_1)

        payload = {
            "order": self.order.id,
            "method": Payment.Method.CASH,
            "amount": "5.00",
            "status": Payment.Status.APPLIED,
        }

        response_1 = self.client.post("/api/payments/", payload)
        response_2 = self.client.post("/api/payments/", payload)
        response_3 = self.client.post("/api/payments/", payload)

        self.assertEqual(response_1.status_code, 201)
        self.assertEqual(response_2.status_code, 201)
        self.assertEqual(response_3.status_code, 429)
