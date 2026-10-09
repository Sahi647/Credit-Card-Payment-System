from decimal import Decimal

from rest_framework import serializers
from .models import Transaction


class TransactionFilterSerializer(serializers.Serializer):
    status = serializers.ChoiceField(
        choices=("ALL", "PENDING", "SUCCESS", "FAILED"),
        required=False,
    )
    min_amount = serializers.DecimalField(
        max_digits=12, decimal_places=2, min_value=Decimal("0"), required=False
    )
    max_amount = serializers.DecimalField(
        max_digits=12, decimal_places=2, min_value=Decimal("0"), required=False
    )
    start_date = serializers.DateField(required=False)
    end_date = serializers.DateField(required=False)

    def validate(self, attrs):
        if (
            "min_amount" in attrs
            and "max_amount" in attrs
            and attrs["min_amount"] > attrs["max_amount"]
        ):
            raise serializers.ValidationError(
                {"max_amount": "Maximum amount must be at least the minimum amount."}
            )
        if (
            "start_date" in attrs
            and "end_date" in attrs
            and attrs["start_date"] > attrs["end_date"]
        ):
            raise serializers.ValidationError(
                {"end_date": "End date must be on or after the start date."}
            )
        return attrs


class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = [
            "id",
            "transaction_id",
            "user_id",
            "payment_id",
            "card_id",
            "card_last_four",
            "amount",
            "status",
            "created_at",
        ]