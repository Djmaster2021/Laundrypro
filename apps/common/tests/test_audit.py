from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from apps.catalog.models import Service
from apps.common.models import AuditLog
from apps.customers.models import Customer
from apps.orders.models import Order, OrderItem
from apps.payments.models import CashSession, Payment


class AuditSignalsTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="auditor", password="StrongPass123!")
        self.customer = Customer.objects.create(first_name="Laura", last_name="Lopez", phone="5511112222")
        self.service = Service.objects.create(
            code="LAV-KG",
            name="Lavado por kilo",
            category=Service.Category.WASH,
            pricing_mode=Service.PricingMode.KILO,
            unit_price=Decimal("25.00"),
            default_iva_rate=Decimal("16.00"),
        )

    def _build_order(self):
        order = Order.objects.create(customer=self.customer)
        OrderItem.objects.create(
            order=order,
            service=self.service,
            pricing_mode=self.service.pricing_mode,
            quantity=Decimal("2.00"),
            unit_price=self.service.unit_price,
            iva_rate=self.service.default_iva_rate,
        )
        order.refresh_financials(persist=True)
        return order

    def test_logs_price_change(self):
        self.service.unit_price = Decimal("30.00")
        self.service.save(update_fields=["unit_price", "updated_at"])

        self.assertTrue(AuditLog.objects.filter(action="service.price_changed", target_pk=str(self.service.pk)).exists())

    def test_logs_order_cancel(self):
        order = self._build_order()
        order.status = Order.Status.CANCELLED
        order.save(update_fields=["status", "updated_at"])

        self.assertTrue(AuditLog.objects.filter(action="order.cancelled", target_pk=str(order.pk)).exists())

    def test_logs_payment_edit_and_void(self):
        order = self._build_order()
        payment = Payment.objects.create(order=order, amount=Decimal("20.00"), method=Payment.Method.CASH)

        payment.amount = Decimal("25.00")
        payment.reference = "AJUSTE-1"
        payment.save(update_fields=["amount", "reference", "updated_at"])

        payment.status = Payment.Status.VOID
        payment.save(update_fields=["status", "updated_at"])

        self.assertTrue(AuditLog.objects.filter(action="payment.created", target_pk=str(payment.pk)).exists())
        self.assertTrue(AuditLog.objects.filter(action="payment.edited", target_pk=str(payment.pk)).exists())
        self.assertTrue(AuditLog.objects.filter(action="payment.voided", target_pk=str(payment.pk)).exists())

    def test_logs_cash_session_close(self):
        session = CashSession.objects.create(
            user=self.user,
            shift=CashSession.Shift.MORNING,
            opening_amount=Decimal("100.00"),
        )

        session.closing_amount = Decimal("150.00")
        session.closed_at = timezone.now()
        session.save(update_fields=["closing_amount", "closed_at", "updated_at"])

        self.assertTrue(AuditLog.objects.filter(action="cash_session.closed", target_pk=str(session.pk)).exists())
