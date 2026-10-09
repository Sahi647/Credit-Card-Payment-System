import csv
from datetime import datetime, time, timedelta
from django.contrib.admin.models import LogEntry, CHANGE
from django.contrib.contenttypes.models import ContentType
from django.db.models import Count, Sum, Q
from django.http import HttpResponse
from django.shortcuts import render
from django.utils import timezone
from .models import Transaction


def log_admin_action(request, object_repr, change_message, action_flag=CHANGE):
    LogEntry.objects.log_action(
        user_id=request.user.pk,
        content_type_id=ContentType.objects.get_for_model(Transaction).pk,
        object_id="0",
        object_repr=object_repr,
        action_flag=action_flag,
        change_message=change_message,
    )


def payment_summary(request):
    today = timezone.localdate()
    current_timezone = timezone.get_current_timezone()
    start_of_day = timezone.make_aware(
        datetime.combine(today, time.min),
        current_timezone,
    )
    start_of_tomorrow = timezone.make_aware(
        datetime.combine(today + timedelta(days=1), time.min),
        current_timezone,
    )
    transactions = Transaction.objects.filter(
        created_at__gte=start_of_day,
        created_at__lt=start_of_tomorrow,
    )
    summary = transactions.aggregate(
        total_transactions=Count("id"),
        successful_payments=Count("id", filter=Q(status="SUCCESS")),
        failed_payments=Count("id", filter=Q(status="FAILED")),
        pending_payments=Count("id", filter=Q(status="PENDING")),
        total_amount=Sum("amount", filter=Q(status="SUCCESS")),
    )
    summary["total_amount"] = summary["total_amount"] or 0
    recent_transactions = transactions.order_by("-created_at")[:20]
    log_admin_action(
        request,
        "Daily payment summary",
        f"Viewed payment summary for {today.isoformat()}.",
        action_flag=CHANGE,
    )
    return render(
        request,
        "admin/payment_summary.html",
        {"summary": summary, "today": today, "transactions": recent_transactions},
    )


def export_transactions_csv(request):
    transactions = Transaction.objects.all().order_by("-created_at")
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="transactions.csv"'
    writer = csv.writer(response)
    writer.writerow(
        ["Transaction ID", "User ID", "Payment ID", "Card ID", "Card", "Amount", "Status", "Date"]
    )

    for transaction in transactions:
        writer.writerow(
            [
                transaction.transaction_id,
                transaction.user_id,
                transaction.payment_id,
                transaction.card_id,
                f"**** **** **** {transaction.card_last_four}",
                transaction.amount,
                transaction.status,
                transaction.created_at,
            ]
        )

    log_admin_action(
        request,
        "Transaction CSV export",
        "Administrator exported transaction records to CSV.",
    )
    return response
