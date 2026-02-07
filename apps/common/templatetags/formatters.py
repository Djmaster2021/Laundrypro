from decimal import Decimal, InvalidOperation

from django import template
from django.utils import timezone

register = template.Library()


@register.filter
def mxn(value):
    if value in (None, ""):
        return "$0.00"
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return "$0.00"
    return f"${number:,.2f}"


@register.filter
def mxdate(value):
    if not value:
        return "-"
    dt = value
    if hasattr(value, "tzinfo"):
        dt = timezone.localtime(value) if timezone.is_aware(value) else value
    return dt.strftime("%d/%m/%Y")


@register.filter
def mxdatetime(value):
    if not value:
        return "-"
    dt = value
    if hasattr(value, "tzinfo"):
        dt = timezone.localtime(value) if timezone.is_aware(value) else value
    return dt.strftime("%d/%m/%Y %H:%M")
