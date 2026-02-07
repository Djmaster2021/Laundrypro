from django.db.models import Count, Sum
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.api_permissions import IsManagerOrAdmin
from apps.customers.models import Customer
from apps.inventory.models import Expense, InventoryMovement
from apps.orders.models import Order, OrderItem
from apps.payments.models import Payment


class AdvancedSummaryAPIView(APIView):
    permission_classes = [IsAuthenticated, IsManagerOrAdmin]

    def get(self, request):
        date_from = self._parse_date(request.GET.get("date_from"), timezone.localdate().replace(day=1))
        date_to = self._parse_date(request.GET.get("date_to"), timezone.localdate())

        sales_total = (
            Payment.objects.filter(status=Payment.Status.APPLIED, paid_at__date__gte=date_from, paid_at__date__lte=date_to)
            .aggregate(total=Sum("amount"))["total"]
            or 0
        )
        expenses_total = (
            Expense.objects.filter(expense_date__gte=date_from, expense_date__lte=date_to).aggregate(total=Sum("amount"))["total"]
            or 0
        )

        frequent_customers = list(
            Customer.objects.filter(orders__received_at__date__gte=date_from, orders__received_at__date__lte=date_to)
            .annotate(orders_count=Count("orders"), sales=Sum("orders__total"))
            .order_by("-orders_count")
            .values("id", "first_name", "last_name", "phone", "orders_count", "sales")[:10]
        )

        top_services = list(
            OrderItem.objects.filter(order__received_at__date__gte=date_from, order__received_at__date__lte=date_to)
            .exclude(order__status=Order.Status.CANCELLED)
            .values("service__name")
            .annotate(total=Sum("total"), count=Count("id"))
            .order_by("-total")[:10]
        )

        supplies_consumption = list(
            InventoryMovement.objects.filter(
                occurred_at__date__gte=date_from,
                occurred_at__date__lte=date_to,
                movement_type__in=[InventoryMovement.MovementType.CONSUMPTION, InventoryMovement.MovementType.LOSS],
            )
            .values("supply__name")
            .annotate(total_qty=Sum("quantity"), count=Count("id"))
            .order_by("-total_qty")[:10]
        )

        pending_count = Order.objects.exclude(status__in=[Order.Status.CANCELLED, Order.Status.DELIVERED]).filter(balance__gt=0).count()
        overdue_count = (
            Order.objects.exclude(status__in=[Order.Status.CANCELLED, Order.Status.DELIVERED])
            .filter(promised_at__lt=timezone.now())
            .count()
        )

        return Response(
            {
                "date_from": str(date_from),
                "date_to": str(date_to),
                "sales_total": sales_total,
                "expenses_total": expenses_total,
                "estimated_profit": sales_total - expenses_total,
                "pending_orders": pending_count,
                "overdue_orders": overdue_count,
                "frequent_customers": frequent_customers,
                "top_services": top_services,
                "supplies_consumption": supplies_consumption,
            }
        )

    def _parse_date(self, raw_value, fallback):
        if not raw_value:
            return fallback
        try:
            return timezone.datetime.strptime(raw_value, "%Y-%m-%d").date()
        except ValueError:
            return fallback
