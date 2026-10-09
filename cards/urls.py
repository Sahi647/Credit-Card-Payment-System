from django.urls import path
from .views import CardListCreateView, CardDeleteView

urlpatterns = [
    path("", CardListCreateView.as_view(), name="cards_api"),
    path("delete/<int:card_id>/", CardDeleteView.as_view(), name="card_delete_api"),
]