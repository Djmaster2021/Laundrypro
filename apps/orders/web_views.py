from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.db.models import Q
from django.shortcuts import redirect, render
from django.utils.dateparse import parse_datetime
from django.utils import timezone
from django.views import View
from django.views.generic import DetailView, TemplateView

from apps.catalog.models import Service
from apps.customers.models import Customer
from apps.payments.models import CashSession, Payment
from apps.accounts.permissions import ROLE_ADMIN, ROLE_MANAGER, ROLE_SELLER, RoleRequiredMixin

from .barcodes import code128_svg
from .models import Order, OrderItem


class DeskSearchView(LoginRequiredMixin, TemplateView):
    template_name = "orders/desk_search.html"
    login_url = "/login/"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        query = self.request.GET.get("q", "").strip()
        orders = Order.objects.select_related("customer").all()

        if query:
            orders = orders.filter(
                Q(folio__icontains=query)
                | Q(customer__phone__icontains=query)
                | Q(customer__first_name__icontains=query)
                | Q(customer__last_name__icontains=query)
            )

        services = Service.objects.filter(is_active=True).order_by("name")
        context["query"] = query
        context["orders"] = orders[:50]
        context["services"] = services
        return context


class DeskCreateOrderView(LoginRequiredMixin, View):
    template_name = "orders/desk_create_order.html"
    login_url = "/login/"

    def get(self, request):
        return self._render()

    def post(self, request):
        errors = []
        services = Service.objects.filter(is_active=True).order_by("name")

        customer = None
        new_customer_data = None
        customer_id = request.POST.get("customer_id", "").strip()
        if customer_id:
            try:
                customer = Customer.objects.get(pk=int(customer_id), is_active=True)
            except (ValueError, Customer.DoesNotExist):
                errors.append("El cliente seleccionado no existe o esta inactivo.")
        else:
            first_name = request.POST.get("customer_first_name", "").strip()
            last_name = request.POST.get("customer_last_name", "").strip()
            phone = request.POST.get("customer_phone", "").strip()

            if not first_name or not phone:
                errors.append("Si no eliges cliente existente, nombre y telefono son obligatorios.")
            else:
                duplicate_name = Customer.objects.filter(
                    is_active=True,
                    first_name=first_name,
                    last_name=last_name,
                ).order_by("id").first()
                existing_customer = Customer.objects.filter(
                    is_active=True,
                    phone=phone,
                ).order_by("id").first()

                if duplicate_name and existing_customer and duplicate_name.id != existing_customer.id:
                    errors.append("Ya existe un cliente con ese nombre y otro con ese telefono. Selecciona cliente existente.")
                elif duplicate_name:
                    customer = duplicate_name
                elif existing_customer:
                    customer = existing_customer
                else:
                    new_customer_data = {
                        "first_name": first_name,
                        "last_name": last_name,
                        "phone": phone,
                    }

        promised_at_value = request.POST.get("promised_at", "").strip()
        promised_at = None
        if promised_at_value:
            promised_at = parse_datetime(promised_at_value)
            if promised_at is None:
                errors.append("Fecha promesa invalida.")

        notes = request.POST.get("notes", "").strip()

        item_service_ids = request.POST.getlist("item_service")
        item_quantities = request.POST.getlist("item_quantity")
        item_unit_prices = request.POST.getlist("item_unit_price")

        parsed_items = []
        for idx, raw_service_id in enumerate(item_service_ids):
            raw_service_id = raw_service_id.strip()
            if not raw_service_id:
                continue

            quantity_raw = (item_quantities[idx] if idx < len(item_quantities) else "").strip()
            unit_price_raw = (item_unit_prices[idx] if idx < len(item_unit_prices) else "").strip()

            try:
                service = services.get(pk=int(raw_service_id))
            except (ValueError, Service.DoesNotExist):
                errors.append(f"Item {idx + 1}: servicio invalido.")
                continue

            try:
                quantity = Decimal(quantity_raw)
                if quantity <= 0:
                    raise InvalidOperation
            except Exception:
                errors.append(f"Item {idx + 1}: cantidad invalida.")
                continue

            if unit_price_raw:
                try:
                    unit_price = Decimal(unit_price_raw)
                    if unit_price < 0:
                        raise InvalidOperation
                except Exception:
                    errors.append(f"Item {idx + 1}: precio unitario invalido.")
                    continue
            else:
                unit_price = service.unit_price

            parsed_items.append(
                {
                    "service": service,
                    "quantity": quantity,
                    "unit_price": unit_price,
                }
            )

        if not parsed_items:
            errors.append("Debes agregar al menos un servicio a la orden.")

        payment_option = request.POST.get("payment_option", "partial").strip()
        if payment_option not in {"partial", "full"}:
            errors.append("Tipo de pago invalido.")
            payment_option = "partial"

        anticipo_raw = request.POST.get("anticipo_amount", "").strip() or "0"
        anticipo_method = request.POST.get("anticipo_method", Payment.Method.CASH)
        anticipo_reference = request.POST.get("anticipo_reference", "").strip()

        try:
            anticipo_amount = Decimal(anticipo_raw)
            if anticipo_amount < 0:
                raise InvalidOperation
        except Exception:
            errors.append("El anticipo es invalido.")
            anticipo_amount = Decimal("0.00")

        allowed_methods = {choice[0] for choice in Payment.Method.choices}
        if anticipo_method not in allowed_methods:
            errors.append("Metodo de anticipo invalido.")

        open_cash_session = CashSession.objects.filter(user=request.user, closed_at__isnull=True).order_by("-opened_at").first()
        requires_payment = payment_option == "full" or anticipo_amount > 0
        if requires_payment and not open_cash_session:
            errors.append("Debes abrir caja antes de registrar anticipo o pago total.")

        if errors:
            return self._render(errors=errors)

        with transaction.atomic():
            if customer is None and new_customer_data is not None:
                customer = Customer.objects.create(**new_customer_data)

            order = Order.objects.create(
                customer=customer,
                promised_at=promised_at,
                notes=notes,
                status=Order.Status.RECEIVED,
            )

            for item in parsed_items:
                OrderItem.objects.create(
                    order=order,
                    service=item["service"],
                    pricing_mode=item["service"].pricing_mode,
                    quantity=item["quantity"],
                    unit_price=item["unit_price"],
                    iva_rate=item["service"].default_iva_rate,
                )

            order.refresh_financials(persist=True)

            if payment_option == "full":
                Payment.objects.create(
                    order=order,
                    cash_session=open_cash_session,
                    captured_by=request.user,
                    method=anticipo_method,
                    status=Payment.Status.APPLIED,
                    amount=order.total,
                    reference=anticipo_reference,
                )
            elif anticipo_amount > 0:
                Payment.objects.create(
                    order=order,
                    cash_session=open_cash_session,
                    captured_by=request.user,
                    method=anticipo_method,
                    status=Payment.Status.APPLIED,
                    amount=anticipo_amount,
                    reference=anticipo_reference,
                )

        return redirect("order-ticket", order_id=order.id)

    def _render(self, errors=None):
        return render(
            self.request,
            self.template_name,
            {
                "services": Service.objects.filter(is_active=True).order_by("name"),
                "customers": Customer.objects.filter(is_active=True).order_by("first_name", "last_name")[:200],
                "payment_methods": Payment.Method.choices,
                "open_cash_session": CashSession.objects.filter(
                    user=self.request.user, closed_at__isnull=True
                ).order_by("-opened_at").first(),
                "errors": errors or [],
                "payment_options": [
                    ("partial", "Anticipo"),
                    ("full", "Pago total"),
                ],
            },
        )


class DeskScanView(LoginRequiredMixin, View):
    template_name = "orders/desk_scan.html"
    login_url = "/login/"

    def get(self, request):
        query = request.GET.get("q", "").strip().upper()
        if query:
            order = Order.objects.filter(folio__iexact=query).first()
            if order:
                return redirect("desk-order-quick", order_id=order.id)
            messages.error(request, "Folio no encontrado.")
            return render(request, self.template_name, {"query": query, "error": "Folio no encontrado."})
        return render(request, self.template_name, {"query": "", "error": ""})


class DeskOrderQuickView(LoginRequiredMixin, View):
    template_name = "orders/desk_order_quick.html"
    login_url = "/login/"

    def get(self, request, order_id):
        return self._render(request, order_id)

    def post(self, request, order_id):
        order = self._get_order(order_id)
        if not order:
            messages.error(request, "Orden no encontrada.")
            return redirect("desk-scan")

        action = request.POST.get("action", "").strip()

        if action == "deliver":
            order.refresh_financials(persist=True)
            if order.status == Order.Status.DELIVERED:
                messages.info(request, "La orden ya estaba entregada.")
            elif order.balance > 0:
                messages.error(request, "No se puede entregar: la orden tiene saldo pendiente.")
            else:
                order.status = Order.Status.DELIVERED
                order.delivered_at = timezone.now()
                order.save(update_fields=["status", "delivered_at", "updated_at"])
                messages.success(request, "Orden entregada correctamente.")
        elif action == "pay":
            open_session = CashSession.objects.filter(user=request.user, closed_at__isnull=True).order_by("-opened_at").first()
            if not open_session:
                messages.error(request, "Debes abrir caja antes de registrar un cobro.")
            else:
                amount_raw = request.POST.get("amount", "").strip()
                method = request.POST.get("method", Payment.Method.CASH)
                reference = request.POST.get("reference", "").strip()
                notes = request.POST.get("notes", "").strip()
                errors = []

                try:
                    amount = Decimal(amount_raw)
                    if amount <= 0:
                        raise InvalidOperation
                except Exception:
                    amount = Decimal("0.00")
                    errors.append("Monto de pago invalido.")

                allowed_methods = {choice[0] for choice in Payment.Method.choices}
                if method not in allowed_methods:
                    errors.append("Metodo de pago invalido.")

                order.refresh_financials(persist=True)
                if amount > order.balance and order.balance > 0:
                    errors.append("El pago no puede ser mayor al saldo pendiente.")

                if not errors and amount > 0:
                    Payment.objects.create(
                        order=order,
                        cash_session=open_session,
                        captured_by=request.user,
                        method=method,
                        status=Payment.Status.APPLIED,
                        amount=amount,
                        reference=reference,
                        notes=notes,
                    )
                    order.refresh_financials(persist=True)
                    messages.success(request, "Pago registrado correctamente.")
                else:
                    for error in errors:
                        messages.error(request, error)
        elif action == "pay_full":
            open_session = CashSession.objects.filter(user=request.user, closed_at__isnull=True).order_by("-opened_at").first()
            if not open_session:
                messages.error(request, "Debes abrir caja antes de registrar un cobro.")
            else:
                method = request.POST.get("method", Payment.Method.CASH)
                reference = request.POST.get("reference", "").strip()
                allowed_methods = {choice[0] for choice in Payment.Method.choices}
                if method not in allowed_methods:
                    messages.error(request, "Metodo de pago invalido.")
                else:
                    order.refresh_financials(persist=True)
                    if order.balance <= 0:
                        messages.info(request, "La orden ya esta liquidada.")
                    else:
                        Payment.objects.create(
                            order=order,
                            cash_session=open_session,
                            captured_by=request.user,
                            method=method,
                            status=Payment.Status.APPLIED,
                            amount=order.balance,
                            reference=reference,
                            notes="Pago total rapido",
                        )
                        order.refresh_financials(persist=True)
                        messages.success(request, "Pago total registrado correctamente.")
        else:
            messages.error(request, "Accion invalida.")

        return redirect("desk-order-quick", order_id=order_id)

    def _get_order(self, order_id):
        return Order.objects.select_related("customer").prefetch_related("items", "payments").filter(id=order_id).first()

    def _render(self, request, order_id, errors=None, notices=None):
        order = self._get_order(order_id)
        open_session = CashSession.objects.filter(user=request.user, closed_at__isnull=True).order_by("-opened_at").first()
        return render(
            request,
            self.template_name,
            {
                "order": order,
                "open_cash_session": open_session,
                "payment_methods": Payment.Method.choices,
                "errors": errors or [],
                "notices": notices or [],
            },
        )


class DeskProductionBoardView(RoleRequiredMixin, TemplateView):
    template_name = "orders/production_board.html"
    login_url = "/login/"
    allowed_roles = (ROLE_ADMIN, ROLE_MANAGER, ROLE_SELLER)

    area_map = {
        "wash": ("wash_status", "Lavado"),
        "dry": ("dry_status", "Secado"),
        "ironing": ("ironing_status", "Planchado"),
    }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        area = self.request.GET.get("area", "wash").strip()
        if area not in self.area_map:
            area = "wash"

        status_field, area_label = self.area_map[area]
        orders = (
            Order.objects.select_related("customer")
            .exclude(status__in=[Order.Status.CANCELLED, Order.Status.DELIVERED])
            .order_by("promised_at", "-created_at")
        )

        if area == "ironing":
            orders = orders.exclude(ironing_status=Order.AreaStatus.NOT_APPLICABLE)

        status_filter = self.request.GET.get("status", "").strip()
        valid_statuses = {value for value, _ in Order.AreaStatus.choices}
        if status_filter in valid_statuses:
            orders = orders.filter(**{status_field: status_filter})

        context.update(
            {
                "area": area,
                "area_label": area_label,
                "status_field": status_field,
                "status_filter": status_filter,
                "status_choices": [c for c in Order.AreaStatus.choices if c[0] != Order.AreaStatus.NOT_APPLICABLE],
                "orders": orders[:100],
            }
        )
        return context

    def post(self, request, *args, **kwargs):
        area = request.POST.get("area", "wash").strip()
        redirect_url = f"/desk/orders/production/?area={area}"
        if area not in self.area_map:
            messages.error(request, "Area invalida.")
            return redirect(redirect_url)

        order_id = request.POST.get("order_id", "").strip()
        new_status = request.POST.get("new_status", "").strip()
        valid_statuses = {choice[0] for choice in Order.AreaStatus.choices if choice[0] != Order.AreaStatus.NOT_APPLICABLE}

        if new_status not in valid_statuses:
            messages.error(request, "Estatus de area invalido.")
            return redirect(redirect_url)

        try:
            order = Order.objects.get(pk=int(order_id))
        except (ValueError, Order.DoesNotExist):
            messages.error(request, "Orden no encontrada.")
            return redirect(redirect_url)

        field_name = self.area_map[area][0]
        if area == "ironing" and order.ironing_status == Order.AreaStatus.NOT_APPLICABLE:
            messages.error(request, "Esta orden no tiene planchado.")
            return redirect(redirect_url)

        setattr(order, field_name, new_status)
        order.save(update_fields=[field_name, "status", "updated_at"])
        messages.success(request, f"Orden {order.folio}: {self.area_map[area][1]} actualizado.")
        return redirect(redirect_url)


class OrderTicketView(LoginRequiredMixin, DetailView):
    model = Order
    template_name = "orders/ticket.html"
    context_object_name = "order"
    pk_url_kwarg = "order_id"
    login_url = "/login/"

    def get_queryset(self):
        return Order.objects.select_related("customer").prefetch_related("items", "payments")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["business_name"] = getattr(settings, "LAUNDRY_NAME", "LaundryPro")
        context["copy_labels"] = ["COPIA CLIENTE", "COPIA MOSTRADOR"]
        context["barcode_svg"] = code128_svg(self.object.folio)
        return context
