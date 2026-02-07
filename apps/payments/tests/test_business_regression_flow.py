import re
from decimal import Decimal

from django.contrib.auth.models import Group
from django.core.management import call_command
from django.test import Client, TestCase
from django.utils import timezone

from apps.catalog.models import Service
from apps.customers.models import Customer
from apps.orders.models import Order
from apps.payments.models import CashSession


class BusinessRegressionFlowTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_roles")

    def setUp(self):
        self.client = Client()
        self.user = self._create_seller_user()
        self.client.force_login(self.user)

        self.customer = Customer.objects.create(first_name="Maria", last_name="Prueba", phone="5511998877")
        self.service = Service.objects.create(
            code="FLW-REG",
            name="Lavado Regresion",
            category=Service.Category.WASH,
            pricing_mode=Service.PricingMode.KILO,
            unit_price=Decimal("50.00"),
            default_iva_rate=Decimal("16.00"),
        )

    def _create_seller_user(self):
        from django.contrib.auth.models import User

        user = User.objects.create_user(username="seller_flow", password="StrongPass123!")
        user.groups.add(Group.objects.get(name="Vendedora"))
        return user

    def test_end_to_end_cash_order_payment_delivery_close_daily(self):
        response_open = self.client.post(
            "/desk/cash/",
            {
                "action": "open",
                "shift": CashSession.Shift.MORNING,
                "opening_amount": "100.00",
                "notes": "Inicio turno test",
            },
        )
        self.assertEqual(response_open.status_code, 302)

        response_order = self.client.post(
            "/desk/orders/new/",
            {
                "customer_id": str(self.customer.id),
                "notes": "Orden regresion",
                "item_service": [str(self.service.id)],
                "item_quantity": ["2"],
                "item_unit_price": ["50.00"],
                "payment_option": "partial",
                "anticipo_amount": "0",
                "anticipo_method": "cash",
            },
        )
        self.assertEqual(response_order.status_code, 302)

        match = re.search(r"/desk/orders/(\d+)/ticket/", response_order.url)
        self.assertIsNotNone(match)
        order_id = int(match.group(1))

        order = Order.objects.get(pk=order_id)
        self.assertGreater(order.total, Decimal("0.00"))

        response_pay = self.client.post(
            f"/desk/orders/{order_id}/quick/",
            {
                "action": "pay_full",
                "method": "cash",
                "reference": "FLOW-TEST",
            },
        )
        self.assertEqual(response_pay.status_code, 302)

        order.refresh_from_db()
        self.assertEqual(order.balance, Decimal("0.00"))

        response_deliver = self.client.post(
            f"/desk/orders/{order_id}/quick/",
            {
                "action": "deliver",
            },
        )
        self.assertEqual(response_deliver.status_code, 302)

        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.DELIVERED)

        open_session = CashSession.objects.get(user=self.user, closed_at__isnull=True)
        expected = open_session.summary()["expected_cash"]

        response_close = self.client.post(
            "/desk/cash/",
            {
                "action": "close",
                "closing_amount": str(expected),
                "closing_notes": "Cierre test",
            },
        )
        self.assertEqual(response_close.status_code, 302)

        open_session.refresh_from_db()
        self.assertIsNotNone(open_session.closed_at)

        today = timezone.localdate().isoformat()
        response_daily = self.client.get(f"/desk/cash/daily/?date={today}")
        self.assertEqual(response_daily.status_code, 200)
        self.assertContains(response_daily, "Cierre diario")
        self.assertContains(response_daily, "Sin ordenes pendientes.")
        self.assertContains(response_daily, "$216.00")
