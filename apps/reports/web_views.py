from decimal import Decimal

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Q, Sum
from django.shortcuts import render
from django.utils import timezone
from django.views import View

from apps.accounts.permissions import ROLE_ADMIN, ROLE_MANAGER, RoleRequiredMixin
from apps.catalog.models import Service
from apps.customers.models import Customer
from apps.inventory.models import Expense, InventoryMovement
from apps.orders.models import Order, OrderItem
from apps.payments.models import Payment


class SalesByTypeReportView(LoginRequiredMixin, View):
    template_name = "reports/sales_by_type.html"
    login_url = "/login/"

    def get(self, request):
        date_from_raw = request.GET.get("date_from", "").strip()
        date_to_raw = request.GET.get("date_to", "").strip()

        today = timezone.localdate()
        date_from = self._parse_date(date_from_raw, today.replace(day=1))
        date_to = self._parse_date(date_to_raw, today)

        items_qs = (
            OrderItem.objects.select_related("service", "order")
            .exclude(order__status=Order.Status.CANCELLED)
            .filter(order__received_at__date__gte=date_from, order__received_at__date__lte=date_to)
        )

        laundry_total = items_qs.exclude(service__category=Service.Category.IRONING).aggregate(total=Sum("total"))["total"] or Decimal(
            "0.00"
        )
        ironing_total = (
            items_qs.filter(service__category=Service.Category.IRONING).aggregate(total=Sum("total"))["total"]
            or Decimal("0.00")
        )

        by_type = (
            items_qs.values("service__category")
            .annotate(total=Sum("total"), items_count=Count("id"))
            .order_by("service__category")
        )

        mixed_orders_count = (
            items_qs.values("order_id")
            .annotate(
                laundry_items=Count("id", filter=~Q(service__category=Service.Category.IRONING)),
                ironing_items=Count("id", filter=Q(service__category=Service.Category.IRONING)),
            )
            .filter(laundry_items__gt=0, ironing_items__gt=0)
            .count()
        )

        top_services = (
            items_qs.values("service__name", "service__category")
            .annotate(total=Sum("total"), qty=Count("id"))
            .order_by("-total")[:10]
        )

        return render(
            request,
            self.template_name,
            {
                "date_from": date_from,
                "date_to": date_to,
                "laundry_total": laundry_total,
                "ironing_total": ironing_total,
                "global_total": laundry_total + ironing_total,
                "by_type": by_type,
                "mixed_orders_count": mixed_orders_count,
                "top_services": top_services,
            },
        )

    def _parse_date(self, raw_value, fallback):
        if not raw_value:
            return fallback
        try:
            return timezone.datetime.strptime(raw_value, "%Y-%m-%d").date()
        except ValueError:
            return fallback


class AdvancedReportsView(RoleRequiredMixin, View):
    template_name = "reports/advanced_dashboard.html"
    login_url = "/login/"
    allowed_roles = (ROLE_ADMIN, ROLE_MANAGER)

    def get(self, request):
        today = timezone.localdate()
        date_from = self._parse_date(request.GET.get("date_from", ""), today.replace(day=1))
        date_to = self._parse_date(request.GET.get("date_to", ""), today)

        sales_total = (
            Payment.objects.filter(status=Payment.Status.APPLIED, paid_at__date__gte=date_from, paid_at__date__lte=date_to)
            .aggregate(total=Sum("amount"))["total"]
            or Decimal("0.00")
        )
        expenses_total = (
            Expense.objects.filter(expense_date__gte=date_from, expense_date__lte=date_to).aggregate(total=Sum("amount"))["total"]
            or Decimal("0.00")
        )

        frequent_customers = (
            Customer.objects.filter(orders__received_at__date__gte=date_from, orders__received_at__date__lte=date_to)
            .annotate(orders_count=Count("orders"), sales=Sum("orders__total"))
            .order_by("-orders_count")[:15]
        )

        top_services = (
            OrderItem.objects.filter(order__received_at__date__gte=date_from, order__received_at__date__lte=date_to)
            .exclude(order__status=Order.Status.CANCELLED)
            .values("service__name", "service__category")
            .annotate(total=Sum("total"), count=Count("id"))
            .order_by("-total")[:15]
        )

        supplies_consumption = (
            InventoryMovement.objects.filter(
                occurred_at__date__gte=date_from,
                occurred_at__date__lte=date_to,
                movement_type__in=[InventoryMovement.MovementType.CONSUMPTION, InventoryMovement.MovementType.LOSS],
            )
            .values("supply__name")
            .annotate(total_qty=Sum("quantity"), count=Count("id"))
            .order_by("-total_qty")[:15]
        )

        pending_orders = (
            Order.objects.select_related("customer")
            .exclude(status__in=[Order.Status.CANCELLED, Order.Status.DELIVERED])
            .filter(balance__gt=0)
            .order_by("-updated_at")[:40]
        )

        overdue_orders = (
            Order.objects.select_related("customer")
            .exclude(status__in=[Order.Status.CANCELLED, Order.Status.DELIVERED])
            .filter(promised_at__isnull=False, promised_at__lt=timezone.now())
            .order_by("promised_at")[:40]
        )

        return render(
            request,
            self.template_name,
            {
                "date_from": date_from,
                "date_to": date_to,
                "sales_total": sales_total,
                "expenses_total": expenses_total,
                "estimated_profit": sales_total - expenses_total,
                "frequent_customers": frequent_customers,
                "top_services": top_services,
                "supplies_consumption": supplies_consumption,
                "pending_orders": pending_orders,
                "overdue_orders": overdue_orders,
            },
        )

    def _parse_date(self, raw_value, fallback):
        if not raw_value:
            return fallback
        try:
            return timezone.datetime.strptime(raw_value, "%Y-%m-%d").date()
        except ValueError:
            return fallback
