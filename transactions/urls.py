from django.urls import path
from .views import TransactionListView, transaction_history, export_transactions_csv


urlpatterns = [
    path("", TransactionListView.as_view(), name="transactions_api"),
    path("web/", transaction_history, name="transaction_history"),
    path("export/", export_transactions_csv, name="export_transactions"),
]