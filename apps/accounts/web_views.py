from django.contrib.auth.views import LoginView, LogoutView
from django.db.models import Count, Q, Sum
from django.shortcuts import redirect
from django.utils import timezone
from django.views.generic import TemplateView, View

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
        sessions_open = CashSession.objects.filter(closed_at__isnull=True).count()

        context.update(
            {
                "date_from": date_from,
                "date_to": date_to,
                "total_income": total_income,
                "orders_total": orders_total,
                "orders_pending": orders_pending,
                "sessions_open": sessions_open,
                "by_seller": by_seller,
                "payment_methods": payment_methods,
                "top_services": top_services,
            }
        )
        return context

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
