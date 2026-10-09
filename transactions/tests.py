import csv
from datetime import timedelta
from decimal import Decimal
from io import StringIO

from django.contrib.admin.models import ADDITION, CHANGE, LogEntry
from django.contrib.auth.models import User
from django.db import connection
from django.test import RequestFactory, TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken

from authentication.roles import CUSTOMER, assign_user_role
from .models import Transaction


class TransactionTableMixin:
    @classmethod
    def setUpClass(cls):
        with connection.schema_editor() as schema_editor:
            schema_editor.create_model(Transaction)
        super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        with connection.schema_editor() as schema_editor:
            schema_editor.delete_model(Transaction)

    def create_transaction(
        self,
        user,
        transaction_id,
        status_value="SUCCESS",
        amount="25.50",
        created_at=None,
    ):
        return Transaction.objects.create(
            transaction_id=transaction_id,
            user_id=user.pk,
            payment_id=f"PAY-{transaction_id}",
            card_id=1,
            card_last_four="4242",
            amount=Decimal(amount),
            status=status_value,
            created_at=created_at or timezone.now(),
        )


class TransactionApiTests(TransactionTableMixin, TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="transaction-owner",
            password="Secure-Transaction-Password-147!",
        )
        assign_user_role(self.user, CUSTOMER)
        self.other_user = User.objects.create_user(
            username="other-transaction-owner",
            password="Secure-Other-Transaction-Password-258!",
        )
        self.client = APIClient()
        token = AccessToken.for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        self.own_transaction = self.create_transaction(
            self.user, "TXN-OWN", amount="25.50"
        )
        self.other_transaction = self.create_transaction(
            self.other_user, "TXN-OTHER", amount="99.00"
        )

    def test_transaction_api_returns_only_authenticated_users_records(self):
        response = self.client.get(reverse("transactions_api"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [item["transaction_id"] for item in response.data],
            [self.own_transaction.transaction_id],
        )

    def test_transaction_filters_validate_status_amount_and_date(self):
        response = self.client.get(
            reverse("transactions_api"),
            {"status": "FAILED", "min_amount": "0.00"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, [])

        for query in (
            {"status": "UNKNOWN"},
            {"min_amount": "not-a-number"},
            {"start_date": "not-a-date"},
            {"min_amount": "50", "max_amount": "10"},
            {"start_date": "2026-05-01", "end_date": "2026-04-01"},
        ):
            with self.subTest(query=query):
                response = self.client.get(reverse("transactions_api"), query)
                self.assertEqual(response.status_code, 400)

    def test_transaction_api_requires_jwt(self):
        self.client.credentials()
        response = self.client.get(reverse("transactions_api"))
        self.assertEqual(response.status_code, 401)

    def test_web_transaction_csv_is_authenticated_and_owner_scoped(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("export_transactions"))
        self.assertEqual(response.status_code, 200)
        rows = list(csv.reader(StringIO(response.content.decode("utf-8"))))
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[1][0], self.own_transaction.transaction_id)
        self.assertEqual(rows[1][2], "**** **** **** 4242")


class AdminTransactionTests(TransactionTableMixin, TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="admin-report-user",
            password="Secure-Admin-Password-369!",
        )
        assign_user_role(self.user, CUSTOMER)
        self.admin = User.objects.create_superuser(
            username="report-admin",
            email="admin@example.com",
            password="Secure-Admin-Password-369!",
        )
        self.client.force_login(self.admin)
        today = timezone.now()
        self.create_transaction(self.user, "TXN-SUCCESS", "SUCCESS", "30.00", today)
        self.create_transaction(self.user, "TXN-FAILED", "FAILED", "12.00", today)
        self.create_transaction(self.user, "TXN-PENDING", "PENDING", "8.00", today)
        self.create_transaction(
            self.user,
            "TXN-OLD",
            "SUCCESS",
            "99.00",
            today - timedelta(days=2),
        )

    def test_admin_summary_shows_daily_counts_and_audit_entry(self):
        response = self.client.get(reverse("admin_payment_summary"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Total Transactions")
        self.assertContains(response, "Total Successful Payment Amount")
        self.assertEqual(response.context["summary"]["total_transactions"], 3)
        self.assertEqual(response.context["summary"]["successful_payments"], 1)
        self.assertEqual(response.context["summary"]["failed_payments"], 1)
        self.assertEqual(response.context["summary"]["pending_payments"], 1)
        self.assertEqual(response.context["summary"]["total_amount"], Decimal("30"))
        self.assertTrue(
            LogEntry.objects.filter(
                user=self.admin,
                action_flag=CHANGE,
                object_repr="Daily payment summary",
            ).exists()
        )

    def test_admin_csv_export_is_staff_only_and_logs_export(self):
        response = self.client.get(reverse("admin_transactions_export"))
        self.assertEqual(response.status_code, 200)
        rows = list(csv.reader(StringIO(response.content.decode("utf-8"))))
        self.assertEqual(len(rows), 5)
        self.assertEqual(rows[1][0], "TXN-SUCCESS")
        self.assertIn("**** **** **** 4242", rows[1])
        self.assertTrue(
            LogEntry.objects.filter(
                user=self.admin,
                object_repr="Transaction CSV export",
            ).exists()
        )

        regular_user_client = self.client_class()
        regular_user_client.force_login(self.user)
        denied = regular_user_client.get(reverse("admin_transactions_export"))
        self.assertEqual(denied.status_code, 302)

    def test_django_admin_exposes_user_management_to_admins(self):
        response = self.client.get(reverse("admin:auth_user_changelist"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Users &amp; access")
        self.assertContains(response, "account-badge--customer")
        self.assertContains(response, "account-badge--active")
        self.assertContains(response, "admin_dashboard.css")
        self.assertContains(response, reverse("admin_create_administrator"))

    def test_administrator_can_create_additional_admin_from_web(self):
        response = self.client.get(reverse("admin_create_administrator"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Create an administrator")

        response = self.client.post(
            reverse("admin_create_administrator"),
            {
                "username": "web-created-admin",
                "email": "web-admin@example.com",
                "password1": "Distinct-Web-Admin-Password-472!",
                "password2": "Distinct-Web-Admin-Password-472!",
            },
        )

        self.assertRedirects(response, reverse("admin:auth_user_changelist"))
        new_admin = User.objects.get(username="web-created-admin")
        self.assertTrue(new_admin.is_staff)
        self.assertFalse(new_admin.is_superuser)
        self.assertTrue(new_admin.check_password("Distinct-Web-Admin-Password-472!"))
        self.assertTrue(new_admin.groups.filter(name="Administrator").exists())
        self.assertTrue(new_admin.has_perm("auth.change_user"))
        self.assertTrue(
            LogEntry.objects.filter(
                user=self.admin,
                object_id=str(new_admin.pk),
                object_repr=new_admin.username,
                action_flag=ADDITION,
            ).exists()
        )

    def test_non_administrator_cannot_create_admin_from_web(self):
        from authentication.roles import SUPPORT

        support = User.objects.create_user(
            username="support-no-create",
            email="support-no-create@example.com",
            password="Secure-Support-Password-472!",
        )
        assign_user_role(support, SUPPORT)
        support_client = self.client_class()
        support_client.force_login(support)

        response = support_client.get(reverse("admin_create_administrator"))

        self.assertEqual(response.status_code, 403)
        self.assertFalse(User.objects.filter(username="web-created-admin").exists())

    def test_admin_creation_rejects_existing_email(self):
        response = self.client.post(
            reverse("admin_create_administrator"),
            {
                "username": "duplicate-email-admin",
                "email": self.admin.email,
                "password1": "Distinct-Web-Admin-Password-472!",
                "password2": "Distinct-Web-Admin-Password-472!",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "This email address is already in use.")
        self.assertFalse(
            User.objects.filter(username="duplicate-email-admin").exists()
        )

    def test_administrator_role_can_open_card_and_transaction_admin_pages(self):
        from authentication.roles import ADMINISTRATOR

        role_admin = User.objects.create_user(
            username="role-admin",
            email="role-admin@example.com",
            password="Secure-Admin-Password-982!",
        )
        assign_user_role(role_admin, ADMINISTRATOR)
        role_admin_client = self.client_class()
        role_admin_client.force_login(role_admin)

        dashboard = role_admin_client.get(reverse("admin:index"))
        self.assertContains(dashboard, "Good to see you.")
        self.assertContains(dashboard, "CARDFLOW · OPERATIONS")
        self.assertContains(dashboard, reverse("admin:cards_card_changelist"))
        self.assertContains(
            dashboard, reverse("admin:transactions_transaction_changelist")
        )
        self.assertEqual(
            role_admin_client.get(
                reverse("admin:cards_card_changelist")
            ).status_code,
            200,
        )
        self.assertEqual(
            role_admin_client.get(
                reverse("admin:transactions_transaction_changelist")
            ).status_code,
            200,
        )

    def test_transaction_admin_is_read_only_and_exposes_export_action(self):
        from django.contrib import admin

        model_admin = admin.site._registry[Transaction]
        request = RequestFactory().get("/")
        request.user = self.admin
        self.assertTrue(model_admin.has_change_permission(request))
        self.assertFalse(model_admin.has_add_permission(request))
        self.assertFalse(model_admin.has_delete_permission(request))
        self.assertIn("export_transactions", model_admin.get_actions(request))
        self.assertEqual(
            set(model_admin.readonly_fields),
            {
                "transaction_id",
                "user_id",
                "payment_id",
                "card_id",
                "card_last_four",
                "amount",
                "status",
                "created_at",
            },
        )
        self.assertIsNone(model_admin.date_hierarchy)

    def test_transaction_admin_changelist_renders_transaction_dates(self):
        response = self.client.get(
            reverse("admin:transactions_transaction_changelist")
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Created at")

    def test_admin_home_links_to_payment_reporting(self):
        response = self.client.get(reverse("admin:index"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Good to see you.")
        self.assertContains(response, "Where would you like to go?")
        self.assertContains(response, "CardFlow | Administration")
        self.assertContains(response, reverse("admin_payment_summary"))
        self.assertContains(response, reverse("admin_transactions_export"))

    def test_support_role_can_review_but_not_export_or_manage(self):
        from authentication.roles import SUPPORT

        support_user = User.objects.create_user(
            username="support-agent",
            password="Secure-Support-Password-741!",
        )
        assign_user_role(support_user, SUPPORT)
        support_client = self.client_class()
        support_client.force_login(support_user)

        self.assertEqual(
            support_client.get(reverse("admin:cards_card_changelist")).status_code,
            200,
        )
        self.assertEqual(
            support_client.get(reverse("admin:transactions_transaction_changelist")).status_code,
            200,
        )
        self.assertEqual(
            support_client.get(reverse("admin_payment_summary")).status_code,
            403,
        )
        self.assertEqual(
            support_client.get(reverse("admin_transactions_export")).status_code,
            403,
        )
        self.assertEqual(
            support_client.get(reverse("admin:auth_user_changelist")).status_code,
            403,
        )
        self.assertEqual(
            support_client.get(reverse("transaction_history")).status_code,
            403,
        )
        dashboard = support_client.get(reverse("admin:index"))
        self.assertNotContains(dashboard, reverse("admin_transactions_export"))
