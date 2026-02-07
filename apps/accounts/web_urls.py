from django.urls import path
from django.contrib.auth.views import PasswordChangeDoneView, PasswordChangeView

from .web_views import (
    AppHomeRedirectView,
    ManagerDashboardView,
    ManagerManualView,
    OperationsManualPrintView,
    POSDashboardView,
    RoleLoginView,
    RoleLogoutView,
    SellerManualView,
)

urlpatterns = [
    path("", AppHomeRedirectView.as_view(), name="app-home"),
    path("login/", RoleLoginView.as_view(), name="login"),
    path("logout/", RoleLogoutView.as_view(), name="logout"),
    path(
        "password/change/",
        PasswordChangeView.as_view(
            template_name="accounts/password_change.html",
            success_url="/password/change/done/",
        ),
        name="password-change",
    ),
    path(
        "password/change/done/",
        PasswordChangeDoneView.as_view(template_name="accounts/password_change_done.html"),
        name="password-change-done",
    ),
    path("manager/", ManagerDashboardView.as_view(), name="manager-dashboard"),
    path("manager/manual/", ManagerManualView.as_view(), name="manager-manual"),
    path("manual/print/", OperationsManualPrintView.as_view(), name="operations-manual-print"),
    path("pos/", POSDashboardView.as_view(), name="pos-dashboard"),
    path("pos/manual/", SellerManualView.as_view(), name="seller-manual"),
]
