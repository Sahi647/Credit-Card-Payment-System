from django.contrib.auth.models import User
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from .roles import ADMINISTRATOR, CUSTOMER, SUPPORT, has_role


class AuthenticationApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="account-owner",
            email="owner@example.com",
            password="Secure-Account-Password-982!",
        )

    def test_registration_hashes_password_and_returns_jwt_tokens(self):
        password = "Distinct-Registration-Password-472!"
        response = self.client.post(
            reverse("auth_register"),
            {
                "username": "new-account",
                "email": "new@example.com",
                "password": password,
                "password_confirm": password,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        created_user = User.objects.get(username="new-account")
        self.assertNotEqual(created_user.password, password)
        self.assertTrue(created_user.check_password(password))
        self.assertTrue(response.data["access"])
        self.assertTrue(response.data["refresh"])
        self.assertTrue(has_role(created_user, CUSTOMER))

    def test_registration_rejects_mismatched_and_weak_passwords(self):
        payload = {
            "username": "new-account",
            "email": "new@example.com",
            "password": "short",
            "password_confirm": "different",
        }
        response = self.client.post(reverse("auth_register"), payload, format="json")
        self.assertEqual(response.status_code, 400)

        payload["password_confirm"] = payload["password"]
        response = self.client.post(reverse("auth_register"), payload, format="json")
        self.assertEqual(response.status_code, 400)

    def test_login_and_profile_require_valid_jwt(self):
        anonymous_response = self.client.get(reverse("auth_profile"))
        self.assertEqual(anonymous_response.status_code, 401)

        login_response = self.client.post(
            reverse("auth_login"),
            {"username": self.user.username, "password": "Secure-Account-Password-982!"},
            format="json",
        )
        self.assertEqual(login_response.status_code, 200)

        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {login_response.data['access']}"
        )
        profile_response = self.client.get(reverse("auth_profile"))
        self.assertEqual(profile_response.status_code, 200)
        self.assertEqual(profile_response.data["id"], self.user.id)

    def test_logout_blacklists_only_authenticated_users_refresh_token(self):
        refresh = RefreshToken.for_user(self.user)
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}"
        )
        response = self.client.post(
            reverse("auth_logout"),
            {"refresh": str(refresh)},
            format="json",
        )
        self.assertEqual(response.status_code, 200)

        response = self.client.post(
            reverse("auth_logout"),
            {"refresh": "invalid-token"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)


class RoleAssignmentTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="role-target",
            password="Secure-Role-Password-582!",
        )

    def test_role_command_assigns_expected_groups_and_admin_access(self):
        call_command("assign_role", self.user.username, ADMINISTRATOR)
        self.user = User.objects.get(pk=self.user.pk)
        self.assertTrue(self.user.is_staff)
        self.assertTrue(has_role(self.user, ADMINISTRATOR))
        self.assertTrue(self.user.has_perm("auth.change_user"))

        call_command("assign_role", self.user.username, SUPPORT)
        self.user = User.objects.get(pk=self.user.pk)
        self.assertTrue(self.user.is_staff)
        self.assertTrue(has_role(self.user, SUPPORT))
        self.assertFalse(self.user.has_perm("auth.change_user"))
        self.assertTrue(self.user.has_perm("cards.view_card"))
        self.assertFalse(self.user.has_perm("cards.delete_card"))

        call_command("assign_role", self.user.username, CUSTOMER)
        self.user = User.objects.get(pk=self.user.pk)
        self.assertFalse(self.user.is_staff)
        self.assertTrue(has_role(self.user, CUSTOMER))
        self.assertFalse(self.user.has_perm("cards.view_card"))

    def test_role_command_rejects_unknown_users(self):
        with self.assertRaises(CommandError):
            call_command("assign_role", "missing-user", CUSTOMER)
