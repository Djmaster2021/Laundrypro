from __future__ import annotations

from django.conf import settings
from decimal import Decimal

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from apps.catalog.models import Service
from apps.orders.models import Order
from apps.payments.models import CashSession, Payment

from .audit import log_audit_event
from .alerts import raise_operational_alert
from .models import OperationalAlert


@receiver(pre_save, sender=Service)
def audit_service_price_change(sender, instance: Service, **kwargs):
    if not instance.pk:
        return
    previous = sender.objects.filter(pk=instance.pk).only("unit_price").first()
    if not previous:
        return
    if previous.unit_price != instance.unit_price:
        log_audit_event(
            "service.price_changed",
            instance,
            changes={"unit_price": (previous.unit_price, instance.unit_price)},
            metadata={"service_code": instance.code, "service_name": instance.name},
        )


@receiver(pre_save, sender=Order)
def audit_order_cancellation(sender, instance: Order, **kwargs):
    if not instance.pk:
        return
    previous = sender.objects.filter(pk=instance.pk).only("status").first()
    if not previous:
        return
    if previous.status != Order.Status.CANCELLED and instance.status == Order.Status.CANCELLED:
        log_audit_event(
            "order.cancelled",
            instance,
            changes={"status": (previous.status, instance.status)},
            metadata={"folio": instance.folio},
        )


@receiver(pre_save, sender=Payment)
def audit_payment_updates(sender, instance: Payment, **kwargs):
    if not instance.pk:
        return

    previous = (
        sender.objects.filter(pk=instance.pk)
        .only("amount", "method", "status", "reference", "cash_session_id")
        .first()
    )
    if not previous:
        return

    tracked_fields = {
        "amount": (previous.amount, instance.amount),
        "method": (previous.method, instance.method),
        "status": (previous.status, instance.status),
        "reference": (previous.reference, instance.reference),
        "cash_session_id": (previous.cash_session_id, instance.cash_session_id),
    }
    changes = {field: values for field, values in tracked_fields.items() if values[0] != values[1]}

    if not changes:
        return

    action = "payment.edited"
    if "status" in changes and changes["status"][1] == Payment.Status.VOID:
        action = "payment.voided"

    log_audit_event(
        action,
        instance,
        changes=changes,
        metadata={
            "order_id": instance.order_id,
            "order_folio": instance.order.folio if instance.order_id else "",
        },
    )


@receiver(pre_save, sender=CashSession)
def audit_cash_session_close(sender, instance: CashSession, **kwargs):
    if not instance.pk:
        return
    previous = sender.objects.filter(pk=instance.pk).only("closed_at", "closing_amount").first()
    if not previous:
        return

    if previous.closed_at is None and instance.closed_at is not None:
        diff = None
        expected_cash = None
        try:
            expected_cash = instance.summary()["expected_cash"]
            if instance.closing_amount is not None:
                diff = Decimal(instance.closing_amount) - Decimal(expected_cash)
        except Exception:
            pass

        log_audit_event(
            "cash_session.closed",
            instance,
            changes={
                "closed_at": (previous.closed_at, instance.closed_at),
                "closing_amount": (previous.closing_amount, instance.closing_amount),
            },
            metadata={"expected_cash": expected_cash, "difference": diff, "session_user_id": instance.user_id},
        )

        threshold = Decimal(str(getattr(settings, "CASH_DIFF_ALERT_THRESHOLD", "200.00")))
        if diff is not None and abs(diff) >= threshold:
            raise_operational_alert(
                event_type="cash_session.high_difference",
                source=f"cash_session:{instance.pk}",
                severity=OperationalAlert.Severity.CRITICAL,
                message="Diferencia de caja alta detectada al cierre.",
                metadata={
                    "cash_session_id": instance.pk,
                    "user_id": instance.user_id,
                    "difference": str(diff),
                    "threshold": str(threshold),
                },
            )


@receiver(post_save, sender=Payment)
def audit_payment_created(sender, instance: Payment, created: bool, **kwargs):
    if not created:
        return
    log_audit_event(
        "payment.created",
        instance,
        metadata={
            "order_id": instance.order_id,
            "order_folio": instance.order.folio if instance.order_id else "",
            "amount": str(instance.amount),
            "method": instance.method,
            "status": instance.status,
        },
    )
