from django.contrib import messages
from django.db.models import Count, F, Sum
from django.shortcuts import redirect, render
from django.utils import timezone
from rest_framework import filters, viewsets
from django.views import View

from apps.accounts.api_permissions import StrictDjangoModelPermissions
from apps.accounts.permissions import ROLE_ADMIN, ROLE_MANAGER, ROLE_SELLER, RoleRequiredMixin

from .models import Expense, InventoryMovement, Supply
from .serializers import ExpenseSerializer, InventoryMovementSerializer, SupplySerializer


class SupplyViewSet(viewsets.ModelViewSet):
    queryset = Supply.objects.all()
    serializer_class = SupplySerializer
    permission_classes = [StrictDjangoModelPermissions]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["code", "name"]
    ordering_fields = ["name", "current_stock", "min_stock", "created_at"]
    ordering = ["name"]


class InventoryMovementViewSet(viewsets.ModelViewSet):
    queryset = InventoryMovement.objects.select_related("supply", "created_by")
    serializer_class = InventoryMovementSerializer
    permission_classes = [StrictDjangoModelPermissions]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["supply__name", "concept", "notes"]
    ordering_fields = ["occurred_at", "quantity", "created_at"]
    ordering = ["-occurred_at"]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class ExpenseViewSet(viewsets.ModelViewSet):
    queryset = Expense.objects.select_related("related_supply", "created_by")
    serializer_class = ExpenseSerializer
    permission_classes = [StrictDjangoModelPermissions]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["description", "notes", "related_supply__name"]
    ordering_fields = ["expense_date", "amount", "created_at"]
    ordering = ["-expense_date"]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class InventoryDashboardView(RoleRequiredMixin, View):
    allowed_roles = (ROLE_ADMIN, ROLE_MANAGER, ROLE_SELLER)
    login_url = "/login/"
    template_name = "inventory/dashboard.html"

    def get(self, request):
        return self._render(request)

    def post(self, request):
        action = request.POST.get("action", "").strip()

        if action == "movement":
            return self._create_movement(request)
        if action == "expense":
            return self._create_expense(request)

        messages.error(request, "Accion invalida.")
        return redirect("inventory-dashboard")

    def _create_movement(self, request):
        payload = {
            "supply": request.POST.get("supply"),
            "movement_type": request.POST.get("movement_type"),
            "quantity": request.POST.get("quantity"),
            "unit_cost": request.POST.get("unit_cost") or 0,
            "concept": request.POST.get("concept"),
            "notes": request.POST.get("movement_notes", ""),
        }
        serializer = InventoryMovementSerializer(data=payload)
        if serializer.is_valid():
            serializer.save(created_by=request.user)
            messages.success(request, "Movimiento de inventario registrado.")
        else:
            messages.error(request, f"No se pudo registrar movimiento: {serializer.errors}")
        return redirect("inventory-dashboard")

    def _create_expense(self, request):
        payload = {
            "category": request.POST.get("category"),
            "amount": request.POST.get("amount"),
            "description": request.POST.get("description"),
            "expense_date": request.POST.get("expense_date"),
            "related_supply": request.POST.get("related_supply") or None,
            "notes": request.POST.get("expense_notes", ""),
        }
        serializer = ExpenseSerializer(data=payload)
        if serializer.is_valid():
            serializer.save(created_by=request.user)
            messages.success(request, "Gasto registrado.")
        else:
            messages.error(request, f"No se pudo registrar gasto: {serializer.errors}")
        return redirect("inventory-dashboard")

    def _render(self, request):
        today = timezone.localdate()
        date_from = self._parse_date(request.GET.get("date_from", ""), today.replace(day=1))
        date_to = self._parse_date(request.GET.get("date_to", ""), today)

        low_stock_supplies = Supply.objects.filter(is_active=True, current_stock__lte=F("min_stock")).order_by("name")

        consumption = (
            InventoryMovement.objects.filter(
                movement_type__in=[InventoryMovement.MovementType.CONSUMPTION, InventoryMovement.MovementType.LOSS],
                occurred_at__date__gte=date_from,
                occurred_at__date__lte=date_to,
            )
            .values("supply__name")
            .annotate(total_qty=Sum("quantity"), moves=Count("id"))
            .order_by("-total_qty")[:10]
        )

        expense_by_category = (
            Expense.objects.filter(expense_date__gte=date_from, expense_date__lte=date_to)
            .values("category")
            .annotate(total=Sum("amount"), count=Count("id"))
            .order_by("-total")
        )
        expense_total = (
            Expense.objects.filter(expense_date__gte=date_from, expense_date__lte=date_to).aggregate(total=Sum("amount"))["total"]
            or 0
        )

        latest_movements = InventoryMovement.objects.select_related("supply", "created_by").order_by("-occurred_at")[:25]
        latest_expenses = Expense.objects.select_related("related_supply", "created_by").order_by("-expense_date", "-created_at")[:25]

        return render(
            request,
            self.template_name,
            {
                "date_from": date_from,
                "date_to": date_to,
                "supplies": Supply.objects.filter(is_active=True).order_by("name"),
                "low_stock_supplies": low_stock_supplies,
                "consumption": consumption,
                "expense_by_category": expense_by_category,
                "expense_total": expense_total,
                "latest_movements": latest_movements,
                "latest_expenses": latest_expenses,
                "movement_type_choices": InventoryMovement.MovementType.choices,
                "expense_category_choices": Expense.Category.choices,
                "today": today,
            },
        )

    def _parse_date(self, raw_value, fallback):
        if not raw_value:
            return fallback
        try:
            return timezone.datetime.strptime(raw_value, "%Y-%m-%d").date()
        except ValueError:
            return fallback
