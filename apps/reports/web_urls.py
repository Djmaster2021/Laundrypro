from django.urls import path

from .web_views import AdvancedReportsView, SalesByTypeReportView

urlpatterns = [
    path("sales-by-type/", SalesByTypeReportView.as_view(), name="report-sales-by-type"),
    path("advanced/", AdvancedReportsView.as_view(), name="report-advanced"),
]
