from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from authentication.permissions import IsCustomer
from authentication.roles import CUSTOMER, role_required
from .models import Card
from .serializers import CardCreateSerializer, CardSerializer


class CardListCreateView(APIView):
    permission_classes = [IsAuthenticated, IsCustomer]

    def get(self, request):
        cards = Card.objects.filter(user=request.user).order_by("-created_at")
        serializer = CardSerializer(cards, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = CardCreateSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        card = serializer.save()
        return Response(CardSerializer(card).data, status=status.HTTP_201_CREATED)


class CardDeleteView(APIView):
    permission_classes = [IsAuthenticated, IsCustomer]

    def delete(self, request, card_id):
        password = request.data.get("password", "")
        if not password or not request.user.check_password(password):
            return Response(
                {"error": "A valid account password is required to delete a card."},
                status=status.HTTP_403_FORBIDDEN
            )

        card = get_object_or_404(Card, id=card_id, user=request.user)
        card.delete()
        return Response({"message": "Card deleted successfully."}, status=status.HTTP_200_OK)


@role_required(CUSTOMER)
def cards_page(request):
    if not request.user.is_authenticated:
        messages.error(request, "Please login first.")
        return redirect("auth_login_page")

    user = request.user
    cards = Card.objects.filter(user=user).order_by("-created_at")

    return render(request, "cards/cards.html", {"cards": cards, "user": user})


@role_required(CUSTOMER)
def add_card_page(request):
    if not request.user.is_authenticated:
        messages.error(request, "Please login first.")
        return redirect("auth_login_page")

    if request.method == "POST":
        user = request.user
        serializer = CardCreateSerializer(
            data=request.POST,
            context={"user": user},
        )
        if not serializer.is_valid():
            for errors in serializer.errors.values():
                for error in errors:
                    messages.error(request, str(error))
            return render(request, "cards/add_card.html", status=400)
        serializer.save()

        messages.success(request, "Your card was added successfully!")
        return redirect("cards_page")

    return render(request, "cards/add_card.html")


@role_required(CUSTOMER)
def delete_card_page(request, card_id):
    if not request.user.is_authenticated:
        messages.error(request, "Please login first.")
        return redirect("auth_login_page")

    if request.method == "POST":
        user = request.user
        password = request.POST.get("password", "")

        if not password or not user.check_password(password):
            messages.error(request, "The password is incorrect. The card was not deleted.")
            return redirect("cards_page")

        card = get_object_or_404(
            Card,
            id=card_id,
            user=user
        )

        card.delete()
        messages.success(request, "Card deleted successfully.")

    return redirect("cards_page")