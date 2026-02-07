from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.views import LoginView, LogoutView
from django.db.models import Count, Q, Sum
from django.shortcuts import redirect
from django.utils import timezone
from django.views.generic import TemplateView, View

from apps.common.models import OperationalAlert
from apps.orders.models import Order, OrderItem
from apps.payments.models import CashSession, Payment

from .permissions import ROLE_ADMIN, ROLE_MANAGER, ROLE_SELLER, RoleRequiredMixin, user_has_any_role


class RoleLoginView(LoginView):
    template_name = "accounts/login.html"
    redirect_authenticated_user = True

    def get_success_url(self):
        user = self.request.user
        if user_has_any_role(user, [ROLE_ADMIN, ROLE_MANAGER]):
            return "/manager/"
        return "/pos/"


class RoleLogoutView(LogoutView):
    next_page = "login"
    http_method_names = ["get", "post", "head", "options"]

    def get(self, request, *args, **kwargs):
        return self.post(request, *args, **kwargs)


class AppHomeRedirectView(View):
    def get(self, request):
        return redirect("login")


class ManagerDashboardView(RoleRequiredMixin, TemplateView):
    template_name = "accounts/manager_dashboard.html"
    login_url = "/login/"
    allowed_roles = (ROLE_ADMIN, ROLE_MANAGER)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        today = timezone.localdate()
        date_from = self._parse_date(self.request.GET.get("date_from", ""), today)
        date_to = self._parse_date(self.request.GET.get("date_to", ""), today)

        payments = Payment.objects.filter(
            status=Payment.Status.APPLIED,
            paid_at__date__gte=date_from,
            paid_at__date__lte=date_to,
        )

        total_income = payments.aggregate(total=Sum("amount"))["total"] or 0
        by_seller = (
            payments.values(
                "captured_by_id",
                "captured_by__username",
                "captured_by__first_name",
                "captured_by__last_name",
            )
            .annotate(total=Sum("amount"), payments_count=Count("id"))
            .order_by("-total")
        )

        payment_methods = (
            payments.values("method")
            .annotate(total=Sum("amount"), count=Count("id"))
            .order_by("-total")
        )

        items = (
            OrderItem.objects.select_related("service", "order")
            .exclude(order__status=Order.Status.CANCELLED)
            .filter(order__received_at__date__gte=date_from, order__received_at__date__lte=date_to)
        )
        top_services = (
            items.values("service__name", "service__category")
            .annotate(total=Sum("total"), qty=Sum("quantity"))
            .order_by("-total")[:10]
        )

        orders_total = Order.objects.filter(received_at__date__gte=date_from, received_at__date__lte=date_to).count()
        orders_pending = (
            Order.objects.exclude(status__in=[Order.Status.CANCELLED, Order.Status.DELIVERED]).filter(balance__gt=0).count()
        )
        overdue_orders = (
            Order.objects.exclude(status__in=[Order.Status.CANCELLED, Order.Status.DELIVERED])
            .filter(promised_at__isnull=False, promised_at__lt=timezone.now())
            .count()
        )
        sessions_open = CashSession.objects.filter(closed_at__isnull=True).count()
        cash_diff_alerts = OperationalAlert.objects.filter(
            event_type="cash_session.high_difference",
            resolved_at__isnull=True,
        ).count()
        db_alerts_recent = OperationalAlert.objects.filter(
            event_type="database.unavailable",
            last_seen_at__gte=timezone.now() - timedelta(hours=24),
        ).count()
        server_error_alerts_recent = OperationalAlert.objects.filter(
            event_type="http.server_error",
            last_seen_at__gte=timezone.now() - timedelta(hours=24),
        ).count()

        executive_traffic = [
            self._make_signal(
                title="Caja",
                value=f"{sessions_open} abiertas",
                ok_text="Operación estable",
                warn_text="Revisar turnos abiertos",
                danger_text="Sin caja activa",
                level=self._traffic_level(sessions_open, warn_at=1, danger_at=0, inverse=True),
                hint="Validar apertura/cierre por turno y diferencias de corte.",
            ),
            self._make_signal(
                title="Pendientes",
                value=str(orders_pending),
                ok_text="Carga sana",
                warn_text="Acumulación moderada",
                danger_text="Acumulación crítica",
                level=self._traffic_level(orders_pending, warn_at=8, danger_at=20),
                hint="Priorizar cobro y seguimiento de entrega.",
            ),
            self._make_signal(
                title="Atraso",
                value=str(overdue_orders),
                ok_text="Sin atraso relevante",
                warn_text="Atraso controlable",
                danger_text="Atraso crítico",
                level=self._traffic_level(overdue_orders, warn_at=4, danger_at=10),
                hint="Ajustar capacidad y comunicación con clientes.",
            ),
            self._make_signal(
                title="Riesgo caja",
                value=str(cash_diff_alerts),
                ok_text="Sin alertas de diferencia alta",
                warn_text="Alertas activas",
                danger_text="Múltiples alertas críticas",
                level=self._traffic_level(cash_diff_alerts, warn_at=1, danger_at=3),
                hint="Auditar cierres y movimientos con mayor diferencia.",
            ),
            self._make_signal(
                title="Base de datos (24h)",
                value=str(db_alerts_recent),
                ok_text="Sin caída detectada",
                warn_text="Evento aislado",
                danger_text="Caídas recurrentes",
                level=self._traffic_level(db_alerts_recent, warn_at=1, danger_at=2),
                hint="Revisar conectividad, pool y disponibilidad de PostgreSQL.",
            ),
            self._make_signal(
                title="Errores 500 (24h)",
                value=str(server_error_alerts_recent),
                ok_text="Sin errores severos",
                warn_text="Errores a revisar",
                danger_text="Inestabilidad crítica",
                level=self._traffic_level(server_error_alerts_recent, warn_at=1, danger_at=5),
                hint="Consultar logs y abrir incidente de corrección.",
            ),
        ]

        at_risk_count = sum(1 for item in executive_traffic if item["level"] in {"warning", "danger"})
        cash_health_score = self._cash_health_score(orders_pending, overdue_orders, cash_diff_alerts, db_alerts_recent)
        recent_pending_orders = (
            Order.objects.select_related("customer")
            .exclude(status__in=[Order.Status.CANCELLED, Order.Status.DELIVERED])
            .filter(balance__gt=0)
            .order_by("-updated_at")[:12]
        )
        recent_overdue_orders = (
            Order.objects.select_related("customer")
            .exclude(status__in=[Order.Status.CANCELLED, Order.Status.DELIVERED])
            .filter(promised_at__isnull=False, promised_at__lt=timezone.now())
            .order_by("promised_at")[:12]
        )

        context.update(
            {
                "date_from": date_from,
                "date_to": date_to,
                "total_income": total_income,
                "orders_total": orders_total,
                "orders_pending": orders_pending,
                "overdue_orders": overdue_orders,
                "sessions_open": sessions_open,
                "executive_traffic": executive_traffic,
                "at_risk_count": at_risk_count,
                "cash_health_score": cash_health_score,
                "recent_pending_orders": recent_pending_orders,
                "recent_overdue_orders": recent_overdue_orders,
                "by_seller": by_seller,
                "payment_methods": payment_methods,
                "top_services": top_services,
            }
        )
        return context

    def _traffic_level(self, value, warn_at, danger_at, inverse=False):
        if inverse:
            if value <= danger_at:
                return "danger"
            if value <= warn_at:
                return "warning"
            return "success"

        if value >= danger_at:
            return "danger"
        if value >= warn_at:
            return "warning"
        return "success"

    def _make_signal(self, *, title, value, ok_text, warn_text, danger_text, level, hint):
        level_text = {
            "success": ok_text,
            "warning": warn_text,
            "danger": danger_text,
        }[level]
        return {
            "title": title,
            "value": value,
            "level": level,
            "level_text": level_text,
            "hint": hint,
        }

    def _cash_health_score(self, pending_count, overdue_count, diff_alerts, db_alerts):
        score = Decimal("100")
        score -= Decimal(min(pending_count, 20)) * Decimal("1.5")
        score -= Decimal(min(overdue_count, 10)) * Decimal("2.0")
        score -= Decimal(min(diff_alerts, 5)) * Decimal("8.0")
        score -= Decimal(min(db_alerts, 3)) * Decimal("10.0")
        return max(score, Decimal("0")).quantize(Decimal("1"))

    def _parse_date(self, raw_value, fallback):
        if not raw_value:
            return fallback
        try:
            return timezone.datetime.strptime(raw_value, "%Y-%m-%d").date()
        except ValueError:
            return fallback


class POSDashboardView(RoleRequiredMixin, TemplateView):
    template_name = "accounts/pos_dashboard.html"
    login_url = "/login/"
    allowed_roles = (ROLE_ADMIN, ROLE_MANAGER, ROLE_SELLER)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        today = timezone.localdate()

        my_payments_today = Payment.objects.filter(
            captured_by=user,
            status=Payment.Status.APPLIED,
            paid_at__date=today,
        )
        my_total_today = my_payments_today.aggregate(total=Sum("amount"))["total"] or 0
        my_count_today = my_payments_today.count()
        open_session = CashSession.objects.filter(user=user, closed_at__isnull=True).order_by("-opened_at").first()

        recent_orders = (
            Order.objects.select_related("customer")
            .filter(Q(payments__captured_by=user) | Q(created_at__date=today))
            .distinct()
            .order_by("-updated_at")[:15]
        )

        context.update(
            {
                "my_total_today": my_total_today,
                "my_count_today": my_count_today,
                "open_session": open_session,
                "recent_orders": recent_orders,
            }
        )
        return context


class ManagerManualView(RoleRequiredMixin, TemplateView):
    template_name = "accounts/manager_manual.html"
    login_url = "/login/"
    allowed_roles = (ROLE_ADMIN, ROLE_MANAGER)


class SellerManualView(RoleRequiredMixin, TemplateView):
    template_name = "accounts/seller_manual.html"
    login_url = "/login/"
    allowed_roles = (ROLE_ADMIN, ROLE_MANAGER, ROLE_SELLER)


class OperationsManualPrintView(RoleRequiredMixin, TemplateView):
    template_name = "accounts/operations_manual_print.html"
    login_url = "/login/"
    allowed_roles = (ROLE_ADMIN, ROLE_MANAGER, ROLE_SELLER)
