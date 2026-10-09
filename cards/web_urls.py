from django.urls import path

from .views import add_card_page, cards_page, delete_card_page

urlpatterns = [
    path("", cards_page, name="cards_page"),
    path("add/", add_card_page, name="add_card_page"),
    path("delete/<int:card_id>/", delete_card_page, name="delete_card_page"),
]
