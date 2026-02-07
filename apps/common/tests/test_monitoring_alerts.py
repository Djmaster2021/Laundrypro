from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.utils import timezone

from apps.common.models import OperationalAlert
from apps.payments.models import CashSession


@override_settings(CASH_DIFF_ALERT_THRESHOLD="10.00")
class MonitoringAlertsTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="ops_user", password="StrongPass123!")

    def test_cash_session_close_with_high_diff_creates_alert(self):
        session = CashSession.objects.create(
            user=self.user,
            shift=CashSession.Shift.MORNING,
            opening_amount=Decimal("100.00"),
        )
        session.closing_amount = Decimal("70.00")
        session.closed_at = timezone.now()
        session.save(update_fields=["closing_amount", "closed_at", "updated_at"])

        self.assertTrue(
            OperationalAlert.objects.filter(
                event_type="cash_session.high_difference",
                source=f"cash_session:{session.pk}",
                severity=OperationalAlert.Severity.CRITICAL,
            ).exists()
        )

    def test_healthcheck_db_failure_emits_alert(self):
        client = Client()
        with patch("apps.common.views.emit_db_down_alert") as emit_mock, patch(
            "apps.common.views.connection.cursor", side_effect=RuntimeError("db down")
        ):
            response = client.get("/health/")

        self.assertEqual(response.status_code, 503)
        emit_mock.assert_called_once()
