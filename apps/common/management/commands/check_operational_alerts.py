from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.common.models import OperationalAlert


class Command(BaseCommand):
    help = "Revisa alertas operativas recientes y retorna exit code 1 si hay criticas activas."

    def add_arguments(self, parser):
        parser.add_argument("--minutes", type=int, default=60, help="Ventana de tiempo para revisar alertas activas.")

    def handle(self, *args, **options):
        since = timezone.now() - timedelta(minutes=options["minutes"])
        alerts = OperationalAlert.objects.filter(resolved_at__isnull=True, last_seen_at__gte=since).order_by("-last_seen_at")

        critical = alerts.filter(severity=OperationalAlert.Severity.CRITICAL)
        if critical.exists():
            self.stderr.write("ALERTAS CRITICAS ACTIVAS:")
            for alert in critical[:20]:
                self.stderr.write(
                    f"- [{alert.last_seen_at:%Y-%m-%d %H:%M:%S}] {alert.event_type} source={alert.source} count={alert.occurrence_count}"
                )
            raise SystemExit(1)

        self.stdout.write("Sin alertas criticas activas en la ventana solicitada.")
