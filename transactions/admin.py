import csv
from django.contrib import admin
from django.contrib.admin.models import CHANGE
from django.http import HttpResponse
from authentication.roles import ADMINISTRATOR, SUPPORT, has_role
from .models import Transaction
from .admin_views import log_admin_action

admin.site.index_template = "admin/payment_admin_index.html"


@admin.action(description="Export selected transactions to CSV")
def export_transactions(modeladmin, request, queryset):
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="transactions.csv"'

    writer = csv.writer(response)

    writer.writerow([
        "Transaction ID",
        "User ID",
        "Payment ID",
        "Card",
        "Amount",
        "Status",
        "Created At",
    ])

    for transaction in queryset:
        writer.writerow([
            transaction.transaction_id,
            transaction.user_id,
            transaction.payment_id,
            f"**** **** **** {transaction.card_last_four}",
            transaction.amount,
            transaction.status,
            transaction.created_at,
        ])

    log_admin_action(
        request,
        "Selected transaction CSV export",
        f"Administrator exported {queryset.count()} selected transaction records.",
        action_flag=CHANGE,
    )
    return response


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ("transaction_id", "user_id", "payment_id", "card_id", "card_last_four", "amount", "status", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("transaction_id", "payment_id", "card_last_four")
    readonly_fields = ("transaction_id", "user_id", "payment_id", "card_id", "card_last_four", "amount", "status", "created_at")
    actions = (export_transactions,)

    def has_module_permission(self, request):
        return has_role(request.user, ADMINISTRATOR) or has_role(request.user, SUPPORT)

    def has_view_permission(self, request, obj=None):
        return has_role(request.user, ADMINISTRATOR) or has_role(request.user, SUPPORT)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return has_role(request.user, ADMINISTRATOR)

    def has_delete_permission(self, request, obj=None):
        return False

    def get_actions(self, request):
        actions = super().get_actions(request)
        if not has_role(request.user, ADMINISTRATOR):
            actions.pop("export_transactions", None)
        return actions