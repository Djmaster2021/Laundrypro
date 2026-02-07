from decimal import Decimal, InvalidOperation
from collections import defaultdict

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.db.models import Count, Q, Sum
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views import View

from apps.orders.models import Order

from .models import CashMovement, CashSession, Payment


class DeskCashSessionView(LoginRequiredMixin, View):
    template_name = "payments/cash_session.html"
    login_url = "/login/"

    def get(self, request):
        return self._render()

    def post(self, request):
        action = request.POST.get("action", "").strip()

        if action == "open":
            return self._open_session(request)
        if action == "close":
            return self._close_session(request)
        if action == "movement":
            return self._create_movement(request)

        return self._render(errors=["Accion invalida."])

    def _open_session(self, request):
        errors = []
        existing = CashSession.objects.filter(user=request.user, closed_at__isnull=True).first()
        if existing:
            errors.append("Ya tienes una caja abierta.")
            return self._render(errors=errors)

        shift = request.POST.get("shift", "").strip()
        opening_amount_raw = request.POST.get("opening_amount", "0").strip() or "0"
        notes = request.POST.get("notes", "").strip()

        allowed_shifts = {choice[0] for choice in CashSession.Shift.choices}
        if shift not in allowed_shifts:
            errors.append("Turno invalido.")

        try:
            opening_amount = Decimal(opening_amount_raw)
            if opening_amount < 0:
                raise InvalidOperation
        except Exception:
            errors.append("Monto de apertura invalido.")
            opening_amount = Decimal("0.00")

        if errors:
            return self._render(errors=errors)

        CashSession.objects.create(
            user=request.user,
            shift=shift,
            opening_amount=opening_amount,
            notes=notes,
        )
        return redirect("desk-cash")

    def _close_session(self, request):
        errors = []
        session = CashSession.objects.filter(user=request.user, closed_at__isnull=True).order_by("-opened_at").first()
        if not session:
            errors.append("No tienes una caja abierta.")
            return self._render(errors=errors)

        closing_amount_raw = request.POST.get("closing_amount", "").strip()
        closing_notes = request.POST.get("closing_notes", "").strip()

        try:
            closing_amount = Decimal(closing_amount_raw)
            if closing_amount < 0:
                raise InvalidOperation
        except Exception:
            errors.append("Monto de cierre invalido.")
            return self._render(errors=errors)

        with transaction.atomic():
            session.closing_amount = closing_amount
            session.closed_at = timezone.now()
            if closing_notes:
                session.notes = f"{session.notes}\n[Cierre] {closing_notes}".strip()
            session.save(update_fields=["closing_amount", "closed_at", "notes", "updated_at"])

        return redirect("desk-cash")

    def _create_movement(self, request):
        errors = []
        session = CashSession.objects.filter(user=request.user, closed_at__isnull=True).order_by("-opened_at").first()
        if not session:
            errors.append("Debes abrir caja antes de registrar movimientos.")
            return self._render(errors=errors)

        movement_type = request.POST.get("movement_type", "").strip()
        amount_raw = request.POST.get("amount", "").strip()
        concept = request.POST.get("concept", "").strip()
        notes = request.POST.get("movement_notes", "").strip()

        allowed_types = {choice[0] for choice in CashMovement.MovementType.choices}
        if movement_type not in allowed_types:
            errors.append("Tipo de movimiento invalido.")

        if not concept:
            errors.append("El concepto es obligatorio.")

        try:
            amount = Decimal(amount_raw)
            if amount <= 0:
                raise InvalidOperation
        except Exception:
            errors.append("Monto invalido para el movimiento.")
            amount = Decimal("0.00")

        if errors:
            return self._render(errors=errors)

        CashMovement.objects.create(
            cash_session=session,
            movement_type=movement_type,
            amount=amount,
            concept=concept,
            notes=notes,
            created_by=request.user,
        )
        return redirect("desk-cash")

    def _render(self, errors=None):
        open_session = CashSession.objects.filter(user=self.request.user, closed_at__isnull=True).order_by("-opened_at").first()
        last_sessions = CashSession.objects.filter(user=self.request.user).order_by("-opened_at")[:10]
        selected_session_id = self.request.GET.get("session", "").strip()

        report_session = None
        if selected_session_id:
            try:
                report_session = CashSession.objects.get(id=int(selected_session_id), user=self.request.user)
            except (ValueError, CashSession.DoesNotExist):
                report_session = open_session
        else:
            report_session = open_session or (last_sessions[0] if last_sessions else None)

        summary = report_session.summary() if report_session else None
        live_summary = open_session.summary() if open_session else None
        payments = (
            report_session.payments.select_related("order", "captured_by").order_by("-paid_at")[:50]
            if report_session
            else []
        )
        movements = report_session.movements.select_related("created_by").order_by("-occurred_at")[:50] if report_session else []
        diff = None
        if report_session and report_session.closing_amount is not None and summary is not None:
            diff = report_session.closing_amount - summary["expected_cash"]
        insights = self._build_session_insights(summary, diff)
        live_insights = self._build_session_insights(live_summary, None)

        return render(
            self.request,
            self.template_name,
            {
                "errors": errors or [],
                "open_session": open_session,
                "last_sessions": last_sessions,
                "report_session": report_session,
                "summary": summary,
                "live_summary": live_summary,
                "payments": payments,
                "movements": movements,
                "difference": diff,
                "insights": insights,
                "live_insights": live_insights,
                "shift_choices": CashSession.Shift.choices,
                "movement_choices": CashMovement.MovementType.choices,
            },
        )

    def _build_session_insights(self, summary, diff):
        if not summary:
            return []

        insights = []
        generated_total = summary["generated_total"]
        expense_total = summary["expense_total"]

        if generated_total > 0:
            expense_ratio = (expense_total / generated_total) * 100
            if expense_ratio >= Decimal("35.00"):
                insights.append(
                    {
                        "level": "error",
                        "text": f"Alerta: egresos altos ({expense_ratio:.1f}% del ingreso generado en la sesion).",
                    }
                )
            elif expense_ratio >= Decimal("20.00"):
                insights.append(
                    {
                        "level": "info",
                        "text": f"Seguimiento: egresos en {expense_ratio:.1f}% del ingreso generado.",
                    }
                )

        if diff is not None:
            abs_diff = abs(diff)
            if abs_diff >= Decimal("200.00"):
                insights.append(
                    {
                        "level": "error",
                        "text": f"Diferencia de cierre alta: ${abs_diff}. Requiere revision inmediata.",
                    }
                )
            elif abs_diff >= Decimal("50.00"):
                insights.append(
                    {
                        "level": "info",
                        "text": f"Diferencia de cierre moderada: ${abs_diff}. Validar cobros y movimientos.",
                    }
                )

        if summary["net_gain"] < 0:
            insights.append(
                {
                    "level": "error",
                    "text": "Sesion en perdida neta. Revisar egresos y ajustes.",
                }
            )

        if not insights:
            insights.append(
                {
                    "level": "success",
                    "text": "Corte estable: ingresos, efectivo esperado y sesion sin alertas mayores.",
                }
            )

        return insights


class DeskCashDailyCloseView(LoginRequiredMixin, View):
    template_name = "payments/cash_daily.html"
    login_url = "/login/"

    def get(self, request):
        context = self._build_context(request)
        return render(request, self.template_name, context)

    def _build_context(self, request):
        selected_date = request.GET.get("date", "").strip()
        if selected_date:
            try:
                report_date = timezone.datetime.strptime(selected_date, "%Y-%m-%d").date()
            except ValueError:
                report_date = timezone.localdate()
        else:
            report_date = timezone.localdate()

        sessions_today = CashSession.objects.select_related("user").filter(opened_at__date=report_date).order_by("opened_at")
        payments_today = Payment.objects.select_related("order", "captured_by", "cash_session").filter(
            status=Payment.Status.APPLIED,
            paid_at__date=report_date,
        )
        movements_today = CashMovement.objects.filter(occurred_at__date=report_date)

        totals = {
            "cash": payments_today.filter(method="cash").aggregate(total=Sum("amount"))["total"] or Decimal("0.00"),
            "card": payments_today.filter(method="card").aggregate(total=Sum("amount"))["total"] or Decimal("0.00"),
            "transfer": payments_today.filter(method="transfer").aggregate(total=Sum("amount"))["total"] or Decimal("0.00"),
            "other": payments_today.filter(method="other").aggregate(total=Sum("amount"))["total"] or Decimal("0.00"),
        }
        totals["income_total"] = sum(totals.values(), Decimal("0.00"))
        totals["movement_income_total"] = (
            movements_today.filter(movement_type=CashMovement.MovementType.INCOME).aggregate(total=Sum("amount"))["total"]
            or Decimal("0.00")
        )
        totals["movement_expense_total"] = (
            movements_today.filter(movement_type=CashMovement.MovementType.EXPENSE).aggregate(total=Sum("amount"))["total"]
            or Decimal("0.00")
        )
        totals["movement_adjustment_total"] = (
            movements_today.filter(movement_type=CashMovement.MovementType.ADJUSTMENT).aggregate(total=Sum("amount"))["total"]
            or Decimal("0.00")
        )
        totals["generated_total"] = totals["income_total"] + totals["movement_income_total"]
        totals["net_gain"] = totals["generated_total"] - totals["movement_expense_total"]

        by_employee = (
            payments_today.values(
                "captured_by_id",
                "captured_by__username",
                "captured_by__first_name",
                "captured_by__last_name",
            )
            .annotate(total=Sum("amount"), payments_count=Count("id"))
            .order_by("-total")
        )

        pending_orders = (
            Order.objects.select_related("customer")
            .filter(balance__gt=0)
            .exclude(status__in=[Order.Status.DELIVERED, Order.Status.CANCELLED])
            .order_by("-updated_at")[:50]
        )

        sessions_summary = []
        employees_by_shift = defaultdict(list)
        expected_cash_total = Decimal("0.00")
        closing_difference_total = Decimal("0.00")
        for session in sessions_today:
            session_totals = session.summary()
            expected_cash_total += session_totals["expected_cash"]
            session_difference = None
            if session.closing_amount is not None:
                session_difference = session.closing_amount - session_totals["expected_cash"]
                closing_difference_total += session_difference
            sessions_summary.append(
                {
                    "session": session,
                    "expected_cash": session_totals["expected_cash"],
                    "income_total": session_totals["income_total"],
                    "generated_total": session_totals["generated_total"],
                    "net_gain": session_totals["net_gain"],
                    "difference": session_difference,
                }
            )
            full_name = f"{session.user.first_name} {session.user.last_name}".strip() or session.user.username
            if full_name not in employees_by_shift[session.get_shift_display()]:
                employees_by_shift[session.get_shift_display()].append(full_name)

        return {
            "report_date": report_date,
            "totals": totals,
            "expected_cash_total": expected_cash_total,
            "closing_difference_total": closing_difference_total,
            "sessions_summary": sessions_summary,
            "employees_by_shift": dict(employees_by_shift),
            "by_employee": by_employee,
            "pending_orders": pending_orders,
        }


class DeskCashDailyPrintView(DeskCashDailyCloseView):
    template_name = "payments/cash_daily_print.html"
