import csv

from django.contrib import messages
from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import redirect, render
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from authentication.permissions import IsCustomer
from authentication.roles import CUSTOMER, role_required
from .models import Transaction
from .serializers import TransactionFilterSerializer, TransactionSerializer


def _validated_filters(query_params):
    fields = ("status", "min_amount", "max_amount", "start_date", "end_date")
    raw_values = {field: query_params.get(field, "") for field in fields}
    serializer = TransactionFilterSerializer(
        data={key: value for key, value in raw_values.items() if value != ""}
    )
    return serializer, serializer.is_valid()


def _filter_transactions(transactions, filters):
    status_filter = filters.get("status")
    if status_filter and status_filter != "ALL":
        transactions = transactions.filter(status=status_filter)
    if "min_amount" in filters:
        transactions = transactions.filter(amount__gte=filters["min_amount"])
    if "max_amount" in filters:
        transactions = transactions.filter(amount__lte=filters["max_amount"])
    if "start_date" in filters:
        transactions = transactions.filter(created_at__date__gte=filters["start_date"])
    if "end_date" in filters:
        transactions = transactions.filter(created_at__date__lte=filters["end_date"])
    return transactions


class TransactionListView(APIView):
    permission_classes = [IsAuthenticated, IsCustomer]

    def get(self, request):
        transactions = Transaction.objects.filter(
            user_id=request.user.id
        ).order_by("-created_at")
        filter_serializer, valid = _validated_filters(request.query_params)
        if not valid:
            raise ValidationError(filter_serializer.errors)

        transactions = _filter_transactions(
            transactions, filter_serializer.validated_data
        )
        return Response(TransactionSerializer(transactions, many=True).data)


@role_required(CUSTOMER)
def transaction_history(request):
    if not request.user.is_authenticated:
        messages.error(request, "Please login first.")
        return redirect("auth_login_page")

    user = request.user
    transactions = Transaction.objects.filter(user_id=user.id).order_by("-created_at")
    filter_serializer, valid = _validated_filters(request.GET)
    if not valid:
        return render(
            request,
            "transactions/transactions.html",
            {
                "user": user,
                "transactions": [],
                "filter_errors": filter_serializer.errors,
                **{
                    field: request.GET.get(field, "")
                    for field in ("status", "min_amount", "max_amount", "start_date", "end_date")
                },
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    filters = filter_serializer.validated_data
    transactions = _filter_transactions(transactions, filters)
    return render(
        request,
        "transactions/transactions.html",
        {
            "user": user,
            "transactions": transactions,
            "status_filter": filters.get("status", ""),
            "min_amount": filters.get("min_amount", ""),
            "max_amount": filters.get("max_amount", ""),
            "start_date": filters.get("start_date", ""),
            "end_date": filters.get("end_date", ""),
        },
    )


@role_required(CUSTOMER)
def export_transactions_csv(request):
    if not request.user.is_authenticated:
        messages.error(request, "Please login first.")
        return redirect("auth_login_page")

    transactions = Transaction.objects.filter(
        user_id=request.user.id
    ).order_by("-created_at")
    filter_serializer, valid = _validated_filters(request.GET)
    if not valid:
        return HttpResponseBadRequest(str(filter_serializer.errors))
    transactions = _filter_transactions(
        transactions, filter_serializer.validated_data
    )

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="transaction_history.csv"'
    writer = csv.writer(response)
    writer.writerow(
        ["Transaction ID", "Payment ID", "Card", "Amount", "Status", "Date"]
    )
    for transaction in transactions:
        writer.writerow(
            [
                transaction.transaction_id,
                transaction.payment_id,
                f"**** **** **** {transaction.card_last_four}",
                transaction.amount,
                transaction.status,
                transaction.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            ]
        )
    return response
