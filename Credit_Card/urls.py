from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse
from authentication.roles import ADMINISTRATOR, role_required
from authentication.admin_views import create_administrator
from transactions.admin_views import (
    export_transactions_csv as export_admin_transactions_csv,
    payment_summary,
)

def home(request): 
    return JsonResponse({"message": "Credit Card API is running.", "status": "success"})

urlpatterns = [
    path("", home, name="home"),
    path(
        "admin/users/create/",
        admin.site.admin_view(
            role_required(ADMINISTRATOR)(create_administrator)
        ),
        name="admin_create_administrator",
    ),
    path(
        "admin/payment-summary/",
        admin.site.admin_view(role_required(ADMINISTRATOR)(payment_summary)),
        name="admin_payment_summary",
    ),
    path(
        "admin/transactions/export/",
        admin.site.admin_view(
            role_required(ADMINISTRATOR)(export_admin_transactions_csv)
        ),
        name="admin_transactions_export",
    ),
    path("admin/", admin.site.urls),
    path("api/auth/", include("authentication.urls")),
    path("api/cards/", include("cards.urls")),
    path("cards/", include("cards.web_urls")),
    path("api/transactions/", include("transactions.urls")),
]