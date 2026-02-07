from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand


ROLE_PERMISSIONS = {
    "Administrador": [
        "view_customer", "add_customer", "change_customer", "delete_customer",
        "view_order", "add_order", "change_order", "delete_order",
        "view_orderitem", "add_orderitem", "change_orderitem", "delete_orderitem",
        "view_payment", "add_payment", "change_payment", "delete_payment",
        "view_service", "add_service", "change_service", "delete_service",
        "view_servicepricehistory", "add_servicepricehistory", "change_servicepricehistory", "delete_servicepricehistory",
        "view_servicepromotion", "add_servicepromotion", "change_servicepromotion", "delete_servicepromotion",
        "view_supply", "add_supply", "change_supply", "delete_supply",
        "view_inventorymovement", "add_inventorymovement", "change_inventorymovement", "delete_inventorymovement",
        "view_expense", "add_expense", "change_expense", "delete_expense",
    ],
    "Encargada": [
        "view_customer", "add_customer", "change_customer",
        "view_order", "add_order", "change_order",
        "view_orderitem", "add_orderitem", "change_orderitem",
        "view_payment", "add_payment", "change_payment",
        "view_service",
        "view_servicepricehistory", "view_servicepromotion", "add_servicepromotion", "change_servicepromotion",
        "view_supply", "add_supply", "change_supply",
        "view_inventorymovement", "add_inventorymovement", "change_inventorymovement",
        "view_expense", "add_expense", "change_expense",
    ],
    "Vendedora": [
        "view_customer", "add_customer", "change_customer",
        "view_order", "add_order", "change_order",
        "view_orderitem", "add_orderitem", "change_orderitem",
        "view_payment", "add_payment", "change_payment",
        "view_service",
        "view_servicepricehistory", "view_servicepromotion",
        "view_supply",
        "view_inventorymovement", "add_inventorymovement",
        "view_expense", "add_expense",
    ],
}


class Command(BaseCommand):
    help = "Crea y actualiza roles base del negocio (Administrador, Encargada, Vendedora)."

    def handle(self, *args, **options):
        for role_name, codenames in ROLE_PERMISSIONS.items():
            group, _ = Group.objects.get_or_create(name=role_name)
            perms = Permission.objects.filter(codename__in=codenames)
            group.permissions.set(perms)
            self.stdout.write(self.style.SUCCESS(f"Rol actualizado: {role_name} ({perms.count()} permisos)"))

        self.stdout.write(self.style.SUCCESS("Roles base creados/actualizados correctamente."))
