from django.db import connection
from django.http import JsonResponse
from django.views import View

from .alerts import emit_db_down_alert


class HealthCheckView(View):
    def get(self, request):
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
            return JsonResponse({"status": "ok", "database": "ok"}, status=200)
        except Exception as exc:
            emit_db_down_alert(exc)
            return JsonResponse({"status": "error", "database": "unavailable"}, status=503)
