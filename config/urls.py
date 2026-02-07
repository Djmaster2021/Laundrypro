from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("", include("apps.accounts.web_urls")),
    path("", include("apps.common.urls")),
    path("admin/", admin.site.urls),
    path("desk/orders/", include("apps.orders.web_urls")),
    path("desk/cash/", include("apps.payments.web_urls")),
    path("desk/inventory/", include("apps.inventory.web_urls")),
    path("desk/reports/", include("apps.reports.web_urls")),
    path("api/accounts/", include("apps.accounts.urls")),
    path("api/customers/", include("apps.customers.urls")),
    path("api/catalog/", include("apps.catalog.urls")),
    path("api/orders/", include("apps.orders.urls")),
    path("api/payments/", include("apps.payments.urls")),
    path("api/inventory/", include("apps.inventory.urls")),
    path("api/reports/", include("apps.reports.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
