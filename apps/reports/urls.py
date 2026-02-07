from django.urls import path

from .views import AdvancedSummaryAPIView

urlpatterns = [
    path("summary/", AdvancedSummaryAPIView.as_view(), name="reports-summary"),
]
