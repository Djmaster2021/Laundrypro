from django.urls import path

from .web_views import (
    DeskCreateOrderView,
    DeskOrderQuickView,
    DeskProductionBoardView,
    DeskScanView,
    DeskSearchView,
    OrderTicketView,
)

urlpatterns = [
    path("new/", DeskCreateOrderView.as_view(), name="desk-order-new"),
    path("search/", DeskSearchView.as_view(), name="desk-search"),
    path("production/", DeskProductionBoardView.as_view(), name="desk-production"),
    path("scan/", DeskScanView.as_view(), name="desk-scan"),
    path("<int:order_id>/quick/", DeskOrderQuickView.as_view(), name="desk-order-quick"),
    path("<int:order_id>/ticket/", OrderTicketView.as_view(), name="order-ticket"),
]
