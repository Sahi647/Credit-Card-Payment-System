from decimal import Decimal
from unittest import TestCase
from unittest.mock import patch

from django.test import TestCase as DjangoTestCase
from fastapi import HTTPException
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from .database import Base
from .models import Payment, Transaction
from .schemas import PaymentCreate
from .services import create_payment, get_payment


class PaymentServiceTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(cls.engine)
        cls.session_factory = sessionmaker(bind=cls.engine)

    @classmethod
    def tearDownClass(cls):
        Base.metadata.drop_all(cls.engine)
        cls.engine.dispose()
        super().tearDownClass()

    def setUp(self):
        self.db = self.session_factory()
        self.addCleanup(self.db.close)
        self.db.query(Transaction).delete()
        self.db.query(Payment).delete()
        self.db.commit()
        self.card = {"id": 17, "user_id": 4, "last_four": "4242"}
        self.get_card = patch(
            "payment_api.services.get_saved_card", return_value=self.card
        )
        self.get_card_mock = self.get_card.start()
        self.addCleanup(self.get_card.stop)

    def _create_payment(
        self,
        user_id=4,
        card_id=17,
        card_last_four="4242",
        amount=Decimal("35.50"),
    ):
        return create_payment(
            self.db,
            user_id,
            card_id,
            card_last_four,
            amount,
        )

    def test_valid_card_creates_successful_payment_and_transaction(self):
        payment = self._create_payment()

        self.assertEqual(payment.status, "SUCCESS")
        self.assertTrue(payment.payment_id.startswith("SIM-PAY-"))
        self.assertEqual(payment.user_id, 4)
        self.assertEqual(payment.card_id, 17)
        self.assertEqual(payment.card_last_four, "4242")
        self.assertEqual(payment.amount, Decimal("35.50"))
        transaction = self.db.query(Transaction).filter_by(
            payment_id=payment.payment_id
        ).one()
        self.assertEqual(transaction.status, "SUCCESS")
        self.assertEqual(transaction.amount, Decimal("35.50"))
        self.assertEqual(transaction.card_last_four, "4242")

    def test_unknown_or_other_users_card_is_rejected(self):
        self.get_card_mock.return_value = None
        with self.assertRaisesRegex(ValueError, "Card not found"):
            self._create_payment(user_id=5)
        self.assertEqual(self.db.query(Payment).count(), 0)
        self.assertEqual(self.db.query(Transaction).count(), 0)

    def test_incorrect_last_four_digits_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "Card number incorrect"):
            self._create_payment(card_last_four="1111")
        self.assertEqual(self.db.query(Payment).count(), 0)
        self.assertEqual(self.db.query(Transaction).count(), 0)

    def test_invalid_amount_is_rejected_without_recording_payment(self):
        for amount, expected_message in (
            (Decimal("-1.00"), "greater than zero"),
            (Decimal("1000000.01"), "exceeds the allowed limit"),
            (Decimal("35.555"), "cannot have more than two decimal places"),
        ):
            with self.subTest(amount=amount):
                with self.assertRaisesRegex(ValueError, expected_message):
                    self._create_payment(amount=amount)
        self.assertEqual(self.db.query(Payment).count(), 0)
        self.assertEqual(self.db.query(Transaction).count(), 0)

    def test_each_valid_request_gets_a_distinct_simulation_payment_id(self):
        first = self._create_payment()
        second = self._create_payment()
        self.assertNotEqual(first.payment_id, second.payment_id)
        self.assertEqual(self.db.query(Payment).count(), 2)
        self.assertEqual(self.db.query(Transaction).count(), 2)

    def test_payment_lookup_is_scoped_to_the_owning_user(self):
        payment = self._create_payment()
        own_payment, _ = get_payment(self.db, payment.payment_id, user_id=4)
        other_users_payment, message = get_payment(
            self.db, payment.payment_id, user_id=5
        )
        self.assertEqual(own_payment.payment_id, payment.payment_id)
        self.assertIsNone(other_users_payment)
        self.assertEqual(message, "Payment not found.")

    def test_payment_api_returns_simulation_disclaimer_on_success(self):
        from .routers import make_payment

        response = make_payment(
            PaymentCreate(
                card_id=17,
                card_last_four="4242",
                amount="35.50",
            ),
            user_id=4,
            db=self.db,
        )
        self.assertEqual(response["status"], "SUCCESS")
        self.assertEqual(response["card_id"], 17)
        self.assertEqual(response["card_last_four"], "4242")
        self.assertEqual(response["amount"], Decimal("35.50"))
        self.assertIn("No real money was charged", response["message"])

    def test_swagger_payment_schema_contains_only_requested_payment_fields(self):
        from .main import app

        operation = app.openapi()["paths"]["/api/payments/"]["post"]
        schema_ref = operation["requestBody"]["content"]["application/json"][
            "schema"
        ]["$ref"]
        schema_name = schema_ref.rsplit("/", 1)[-1]
        schema = app.openapi()["components"]["schemas"][schema_name]
        self.assertEqual(
            set(schema["properties"]),
            {"card_id", "card_last_four", "amount"},
        )


class PaymentApiAuthorizationTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.engine = create_engine("sqlite:///:memory:")
        with cls.engine.begin() as connection:
            connection.exec_driver_sql(
                "CREATE TABLE auth_user (id INTEGER PRIMARY KEY, is_active BOOLEAN NOT NULL, is_superuser BOOLEAN NOT NULL DEFAULT 0)"
            )
            connection.exec_driver_sql(
                "CREATE TABLE auth_group (id INTEGER PRIMARY KEY, name VARCHAR(150) NOT NULL)"
            )
            connection.exec_driver_sql(
                "CREATE TABLE auth_user_groups (user_id INTEGER NOT NULL, group_id INTEGER NOT NULL)"
            )
        cls.session_factory = sessionmaker(bind=cls.engine)

    @classmethod
    def tearDownClass(cls):
        cls.engine.dispose()
        super().tearDownClass()

    def setUp(self):
        from .auth import get_current_user_id

        self.get_current_user_id = get_current_user_id
        self.db = self.session_factory()
        self.addCleanup(self.db.close)
        self.db.execute(text("DELETE FROM auth_user"))
        self.db.execute(text("INSERT INTO auth_user (id, is_active) VALUES (7, 1)"))
        self.db.execute(text("DELETE FROM auth_user_groups"))
        self.db.execute(text("DELETE FROM auth_group"))
        self.db.execute(text("INSERT INTO auth_group (id, name) VALUES (3, 'Customer')"))
        self.db.execute(
            text("INSERT INTO auth_user_groups (user_id, group_id) VALUES (7, 3)")
        )
        self.db.commit()

    def _access_token(self, token_type="access", user_id="7"):
        from datetime import datetime, timedelta, timezone

        import jwt
        from django.conf import settings

        return jwt.encode(
            {
                "user_id": user_id,
                "token_type": token_type,
                "iat": datetime.now(timezone.utc),
                "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
            },
            settings.SECRET_KEY,
            algorithm="HS256",
        )

    def test_valid_access_token_identifies_active_user(self):
        self.assertEqual(self.get_current_user_id(self._access_token(), self.db), 7)

    def test_missing_refresh_or_unknown_user_token_is_rejected(self):
        for token in (
            None,
            self._access_token(token_type="refresh"),
            self._access_token(user_id="999"),
        ):
            with self.subTest(token=token):
                with self.assertRaises(HTTPException) as error:
                    self.get_current_user_id(token, self.db)
                self.assertEqual(error.exception.status_code, 401)

    def test_oauth2_bearer_scheme_uses_django_jwt_login_url(self):
        from .auth import oauth2_scheme

        self.assertEqual(oauth2_scheme.model.flows.password.tokenUrl, "/api/auth/login/")

    def test_payment_role_guard_allows_customers_and_denies_support(self):
        from authentication.roles import CUSTOMER
        from .auth import require_roles

        customer_guard = require_roles(CUSTOMER)
        self.assertEqual(customer_guard(user_id=7, db=self.db), 7)
        self.db.execute(text("UPDATE auth_group SET name = 'Support' WHERE id = 3"))
        self.db.commit()
        with self.assertRaises(HTTPException) as error:
            customer_guard(user_id=7, db=self.db)
        self.assertEqual(error.exception.status_code, 403)


class OAuth2LoginEndpointTests(DjangoTestCase):
    def setUp(self):
        from django.contrib.auth.models import User

        self.user = User.objects.create_user(
            username="oauth-form-user",
            password="correct-test-password",
        )

    def test_oauth_form_login_returns_django_signed_access_token(self):
        from django.conf import settings

        import jwt

        from .auth_router import oauth_login

        response = oauth_login(
            username=self.user.username,
            password="correct-test-password",
        )
        claims = jwt.decode(
            response["access_token"], settings.SECRET_KEY, algorithms=["HS256"]
        )
        self.assertEqual(response["token_type"], "bearer")
        self.assertEqual(claims["user_id"], str(self.user.pk))
        self.assertEqual(claims["token_type"], "access")
        self.assertTrue(response["refresh_token"])

    def test_oauth_form_login_rejects_invalid_credentials(self):
        from .auth_router import oauth_login

        with self.assertRaises(HTTPException) as error:
            oauth_login(username=self.user.username, password="incorrect")
        self.assertEqual(error.exception.status_code, 401)

    def test_swagger_login_form_only_documents_username_and_password(self):
        from .main import app

        operation = app.openapi()["paths"]["/api/auth/login/"]["post"]
        schema_ref = operation["requestBody"]["content"][
            "application/x-www-form-urlencoded"
        ]["schema"]["$ref"]
        schema_name = schema_ref.rsplit("/", 1)[-1]
        schema = app.openapi()["components"]["schemas"][schema_name]
        self.assertEqual(set(schema["properties"]), {"username", "password"})
        self.assertEqual(set(schema["required"]), {"username", "password"})
