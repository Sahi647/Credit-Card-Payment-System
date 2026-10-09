import re
from datetime import date

from rest_framework import serializers
from .models import Card


class CardCreateSerializer(serializers.Serializer):
    card_type = serializers.ChoiceField(choices=Card.CARD_TYPES, default="Credit")
    card_holder = serializers.CharField(max_length=100, trim_whitespace=True)
    card_number = serializers.CharField(write_only=True, trim_whitespace=True)
    expiry = serializers.CharField(max_length=5, trim_whitespace=True)
    cvv = serializers.CharField(write_only=True, trim_whitespace=True)

    def validate_card_number(self, value):
        digits = re.sub(r"\s+", "", value)
        if not digits.isascii() or not digits.isdigit() or len(digits) != 16:
            raise serializers.ValidationError("Card number must contain exactly 16 digits.")
        return digits

    def validate_expiry(self, value):
        if not re.fullmatch(r"(0[1-9]|1[0-2])/\d{2}", value):
            raise serializers.ValidationError("Expiry must use MM/YY format.")
        month, short_year = (int(part) for part in value.split("/"))
        year = 2000 + short_year
        today = date.today()
        if (year, month) < (today.year, today.month):
            raise serializers.ValidationError("Card has expired.")
        return value

    def validate_cvv(self, value):
        if not value.isascii() or not value.isdigit() or len(value) not in (3, 4):
            raise serializers.ValidationError("CVV must contain 3 or 4 digits.")
        return value

    def create(self, validated_data):
        card_number = validated_data.pop("card_number")
        validated_data.pop("cvv")
        user = self.context.get("user") or self.context["request"].user
        return Card.objects.create(
            user=user,
            masked_number=f"**** **** **** {card_number[-4:]}",
            last_four=card_number[-4:],
            **validated_data,
        )


class CardSerializer(serializers.ModelSerializer):
    class Meta:
        model = Card
        fields = ["id", "card_type", "card_holder", "masked_number", "last_four", "expiry", "created_at"]
        read_only_fields = ["id", "masked_number", "last_four", "created_at"]