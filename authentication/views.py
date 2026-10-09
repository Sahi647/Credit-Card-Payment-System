from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.shortcuts import render, redirect, get_object_or_404

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework import status

from .serializers import RegisterSerializer
from .roles import CUSTOMER, assign_user_role


class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)

        if serializer.is_valid():
            user = serializer.save()
            refresh = RefreshToken.for_user(user)

            return Response({
                "message": "Registration successful.",
                "user_id": user.id,
                "username": user.username,
                "access": str(refresh.access_token),
                "refresh": str(refresh)
            }, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh_token = request.data.get("refresh")

        if not refresh_token:
            return Response(
                {"error": "Refresh token is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            token = RefreshToken(refresh_token)
            if token.payload.get("user_id") != str(request.user.pk):
                raise TokenError("Refresh token belongs to a different user.")
            token.blacklist()

            return Response({"message": "Logout successful."})

        except TokenError:
            return Response(
                {"error": "Invalid or expired refresh token."},
                status=status.HTTP_400_BAD_REQUEST
            )


class ProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({
            "id": request.user.id,
            "username": request.user.username,
            "email": request.user.email
        })


def home(request):
    if "user_id" in request.session:
        return redirect("auth_profile_page")

    return redirect("auth_login_page")


def register_page(request):
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        email = request.POST.get("email", "").strip()
        password = request.POST.get("password", "")
        password_confirm = request.POST.get("password_confirm", "")

        if not username or not email or not password:
            messages.error(request, "Please fill in all fields.")
            return render(request, "authentication/register.html")

        if password != password_confirm:
            messages.error(request, "Passwords do not match.")
            return render(request, "authentication/register.html")

        try:
            validate_password(password, user=User(username=username, email=email))
        except ValidationError as error:
            for message in error.messages:
                messages.error(request, message)
            return render(request, "authentication/register.html", status=400)

        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists.")
            return render(request, "authentication/register.html")

        if User.objects.filter(email=email).exists():
            messages.error(request, "Email already exists.")
            return render(request, "authentication/register.html")

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password
        )
        assign_user_role(user, CUSTOMER)

        messages.success(request, "Registration successful. Please login.")
        return redirect("auth_login_page")

    return render(request, "authentication/register.html")


def login_page(request):
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")

        user = authenticate(
            request,
            username=username,
            password=password
        )

        if user is None:
            messages.error(request, "Invalid username or password.")
            return render(request, "authentication/login.html")

        login(request, user)

        request.session["user_id"] = user.id
        request.session["username"] = user.username

        refresh = RefreshToken.for_user(user)

        request.session["access_token"] = str(refresh.access_token)
        request.session["refresh_token"] = str(refresh)

        return redirect("auth_profile_page")

    return render(request, "authentication/login.html")


def profile_page(request):
    if "user_id" not in request.session:
        messages.error(request, "Please login first.")
        return redirect("auth_login_page")

    user = get_object_or_404(
        User,
        id=request.session["user_id"]
    )

    return render(
        request,
        "authentication/profile.html",
        {"user": user}
    )


def logout_page(request):
    logout(request)
    request.session.flush()

    messages.success(
        request,
        "You have been logged out successfully."
    )

    return redirect("auth_login_page")