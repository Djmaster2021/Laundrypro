import os

from django.contrib.auth.models import Group, User
from django.core.management.base import BaseCommand

EMPLOYEES = [
    {
        "username": "ana",
        "first_name": "Ana",
        "last_name": "",
        "role": "Vendedora",
        "suggested_shift": "Mañana",
        "password_env": "LAUNDRY_POS_ANA_PASSWORD",
        "default_password": "ana123",
    },
    {
        "username": "sofia",
        "first_name": "Sofia",
        "last_name": "",
        "role": "Vendedora",
        "suggested_shift": "Tarde",
        "password_env": "LAUNDRY_POS_SOFIA_PASSWORD",
        "default_password": "sofi123",
    },
]


class Command(BaseCommand):
    help = "Genera empleados base por turno con usuarios y roles asignados."

    def handle(self, *args, **options):
        for employee in EMPLOYEES:
            user, created = User.objects.get_or_create(
                username=employee["username"],
                defaults={
                    "first_name": employee["first_name"],
                    "last_name": employee["last_name"],
                    "is_active": True,
                },
            )

            if not created:
                user.first_name = employee["first_name"]
                user.last_name = employee["last_name"]
                user.is_active = True

            password = os.getenv(employee["password_env"], employee["default_password"])
            user.set_password(password)
            user.save()

            role_group, _ = Group.objects.get_or_create(name=employee["role"])
            user.groups.clear()
            user.groups.add(role_group)

            state = "creado" if created else "actualizado"
            self.stdout.write(
                self.style.SUCCESS(
                    f"Usuario {state}: {user.username} | {employee['first_name']} {employee['last_name']} | "
                    f"rol={employee['role']} | turno sugerido={employee['suggested_shift']}"
                )
            )

        self.stdout.write(self.style.SUCCESS("Empleados base listos: ana / sofia."))
        self.stdout.write(
            self.style.WARNING(
                "Recomendacion: define LAUNDRY_POS_ANA_PASSWORD y LAUNDRY_POS_SOFIA_PASSWORD para no usar claves por defecto."
            )
        )
