from django.core.management import BaseCommand, call_command


class Command(BaseCommand):
    help = "Configura un entorno base para POS: migra y carga datos iniciales."

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Aplicando migraciones..."))
        call_command("migrate", interactive=False)

        self.stdout.write(self.style.NOTICE("Cargando roles..."))
        call_command("seed_roles")

        self.stdout.write(self.style.NOTICE("Cargando empleados..."))
        call_command("seed_employees")

        self.stdout.write(self.style.NOTICE("Cargando catalogo de servicios..."))
        call_command("seed_catalog")

        self.stdout.write(self.style.SUCCESS("Bootstrap POS completado."))
