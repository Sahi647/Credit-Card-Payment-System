from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from .roles import CUSTOMER, assign_user_role


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[validate_password]
    )

    password_confirm = serializers.CharField(
        write_only=True,
        required=True
    )

    class Meta:
        model = User
        fields = [
            "username",
            "email",
            "password",
            "password_confirm"
        ]

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("This email address is already in use.")
        return value

    def validate(self, data):
        if data["password"] != data["password_confirm"]:
            raise serializers.ValidationError({
                "password": "Passwords do not match."
            })

        return data

    def create(self, validated_data):
        validated_data.pop("password_confirm")

        user = User.objects.create_user(**validated_data)
        assign_user_role(user, CUSTOMER)
        return user