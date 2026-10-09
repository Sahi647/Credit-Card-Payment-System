from datetime import date
from unittest.mock import Mock, patch
from types import SimpleNamespace

from django.contrib.auth.models import User
from django.contrib.messages import get_messages
from django.contrib.messages.storage.fallback import FallbackStorage
from django.contrib.sessions.middleware import SessionMiddleware
from django.template.loader import render_to_string
from django.test import RequestFactory, TestCase
from django.urls import reverse
from rest_framework.test import APIClient, APIRequestFactory, force_authenticate
from rest_framework_simplejwt.tokens import AccessToken

from authentication.roles import CUSTOMER, assign_user_role
from .models import Card
from .views import CardDeleteView, delete_card_page


class CardDeletePasswordTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="test-user",
            password="correct-password",
        )
        assign_user_role(self.user, CUSTOMER)
        self.card = Mock()

    @patch("cards.views.get_object_or_404")
    def test_web_delete_rejects_incorrect_password(self, get_object):
        request = RequestFactory().post("/", {"password": "wrong-password"})
        SessionMiddleware(lambda request: None).process_request(request)
        request.session["user_id"] = 1
        request.user = self.user
        request._messages = FallbackStorage(request)

        response = delete_card_page(request, card_id=3)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/cards/")
        self.assertIn(
            "The password is incorrect. The card was not deleted.",
            [str(message) for message in get_messages(request)],
        )
        self.card.delete.assert_not_called()
        get_object.assert_not_called()

    @patch("cards.views.get_object_or_404")
    def test_web_delete_rejects_missing_password(self, get_object):
        request = RequestFactory().post("/", {})
        SessionMiddleware(lambda request: None).process_request(request)
        request.session["user_id"] = 1
        request.user = self.user
        request._messages = FallbackStorage(request)

        response = delete_card_page(request, card_id=3)

        self.assertEqual(response.status_code, 302)
        self.card.delete.assert_not_called()
        get_object.assert_not_called()

    @patch("cards.views.get_object_or_404")
    def test_web_delete_requires_correct_password(self, get_object):
        get_object.return_value = self.card
        request = RequestFactory().post("/", {"password": "correct-password"})
        SessionMiddleware(lambda request: None).process_request(request)
        request.session["user_id"] = 1
        request.user = self.user
        request._messages = FallbackStorage(request)

        response = delete_card_page(request, card_id=3)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/cards/")
        self.card.delete.assert_called_once()
        get_object.assert_any_call(Card, id=3, user=self.user)

    @patch("cards.views.get_object_or_404")
    def test_api_delete_rejects_incorrect_password(self, get_object):
        request = APIRequestFactory().delete(
            "/api/cards/delete/3/",
            {"password": "wrong-password"},
            format="json",
        )
        force_authenticate(request, user=self.user)

        response = CardDeleteView.as_view()(request, card_id=3)

        self.assertEqual(response.status_code, 403)
        get_object.assert_not_called()

    @patch("cards.views.get_object_or_404")
    def test_api_delete_rejects_missing_password(self, get_object):
        request = APIRequestFactory().delete(
            "/api/cards/delete/3/",
            {},
            format="json",
        )
        force_authenticate(request, user=self.user)

        response = CardDeleteView.as_view()(request, card_id=3)

        self.assertEqual(response.status_code, 403)
        get_object.assert_not_called()

    @patch("cards.views.get_object_or_404")
    def test_api_delete_requires_correct_password(self, get_object):
        get_object.return_value = self.card
        request = APIRequestFactory().delete(
            "/api/cards/delete/3/",
            {"password": "correct-password"},
            format="json",
        )
        force_authenticate(request, user=self.user)

        response = CardDeleteView.as_view()(request, card_id=3)

        self.assertEqual(response.status_code, 200)
        get_object.assert_called_once_with(Card, id=3, user=self.user)
        self.card.delete.assert_called_once()

    def test_cards_template_opens_password_prompt_only_after_delete_click(self):
        request = RequestFactory().get("/cards/")
        card = SimpleNamespace(
            id=3,
            card_type="Credit",
            card_holder="Test User",
            masked_number="**** **** **** 4242",
            last_four="4242",
            expiry="12/29",
        )

        html = render_to_string(
            "cards/cards.html",
            {"cards": [card], "messages": []},
            request=request,
        )

        self.assertIn('class="saved-card-side" aria-label="Front of card"', html)
        self.assertIn('class="saved-card-side" aria-label="Back of card"', html)
        self.assertIn('data-delete-dialog="delete-dialog-3"', html)
        self.assertIn('<dialog class="delete-dialog" id="delete-dialog-3"', html)
        before_dialog, dialog_content = html.split('<dialog class="delete-dialog"', 1)
        self.assertNotIn('name="password"', before_dialog)
        self.assertIn('name="password"', dialog_content)


class CustomerCardPageRoleTests(TestCase):
    def test_roleless_regular_user_is_assigned_customer_and_can_open_cards(self):
        user = User.objects.create_user(
            username="legacy-customer",
            password="Secure-Account-Password-982!",
        )
        self.client.force_login(user)

        response = self.client.get(reverse("cards_page"))

        self.assertEqual(response.status_code, 200)
        user.refresh_from_db()
        self.assertTrue(user.groups.filter(name=CUSTOMER).exists())

    def test_support_user_is_not_promoted_to_customer(self):
        user = User.objects.create_user(
            username="support-account",
            password="Secure-Account-Password-982!",
        )
        assign_user_role(user, "Support")
        self.client.force_login(user)

        response = self.client.get(reverse("cards_page"))

        self.assertEqual(response.status_code, 403)
        self.assertTrue(user.groups.filter(name="Support").exists())
        self.assertFalse(user.groups.filter(name=CUSTOMER).exists())


class CardApiTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="card-owner",
            password="Secure-Card-Password-482!",
        )
        assign_user_role(self.user, CUSTOMER)
        self.other_user = User.objects.create_user(
            username="different-owner",
            password="Secure-Other-Password-593!",
        )
        self.client = APIClient()
        token = AccessToken.for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    def test_card_creation_stores_only_masked_number_and_last_four(self):
        response = self.client.post(
            reverse("cards_api"),
            {
                "card_type": "Credit",
                "card_holder": "Card Owner",
                "card_number": "4111 1111 1111 4242",
                "expiry": f"12/{(date.today().year + 2) % 100:02d}",
                "cvv": "123",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        card = Card.objects.get(user=self.user)
        self.assertEqual(card.last_four, "4242")
        self.assertEqual(card.masked_number, "**** **** **** 4242")
        self.assertNotIn("card_number", response.data)
        self.assertNotIn("cvv", response.data)
        self.assertNotIn("4111111111114242", str(card.__dict__))
        self.assertNotIn("123", str(card.__dict__))

    def test_card_creation_rejects_invalid_card_values(self):
        response = self.client.post(
            reverse("cards_api"),
            {
                "card_type": "Unknown",
                "card_holder": "Card Owner",
                "card_number": "4111111111114242",
                "expiry": "13/29",
                "cvv": "12x",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Card.objects.count(), 0)

    def test_card_list_and_delete_are_scoped_to_authenticated_owner(self):
        own_card = Card.objects.create(
            user=self.user,
            card_type="Credit",
            card_holder="Card Owner",
            masked_number="**** **** **** 4242",
            last_four="4242",
            expiry="12/30",
        )
        other_card = Card.objects.create(
            user=self.other_user,
            card_type="Debit",
            card_holder="Other Owner",
            masked_number="**** **** **** 9876",
            last_four="9876",
            expiry="12/30",
        )

        response = self.client.get(reverse("cards_api"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual([item["id"] for item in response.data], [own_card.id])

        response = self.client.delete(
            reverse("card_delete_api", args=[other_card.id]),
            {"password": "Secure-Card-Password-482!"},
            format="json",
        )
        self.assertEqual(response.status_code, 404)
        self.assertTrue(Card.objects.filter(pk=other_card.pk).exists())

    def test_card_api_rejects_requests_without_jwt(self):
        self.client.credentials()
        response = self.client.get(reverse("cards_api"))
        self.assertEqual(response.status_code, 401)
