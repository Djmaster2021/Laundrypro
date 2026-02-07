from django.urls import path

from .web_views import DeskCashDailyCloseView, DeskCashDailyPrintView, DeskCashSessionView

urlpatterns = [
    path("", DeskCashSessionView.as_view(), name="desk-cash"),
    path("daily/", DeskCashDailyCloseView.as_view(), name="desk-cash-daily"),
    path("daily/print/", DeskCashDailyPrintView.as_view(), name="desk-cash-daily-print"),
]
