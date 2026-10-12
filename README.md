# Credit Card Payment System

A local credit-card application with Django REST authentication, card
management, transaction history, an administrator panel, and a separate
FastAPI payment simulator. Both services use the configured Django database
and JWT signing key. Payments are simulations only; no real money is charged.

## Requirements

- Python 3.10 or newer
- MySQL 8 (recommended) or SQLite for local development
- A virtual environment and the packages in `requirements.txt`

## Setup and execution

1. Create a virtual environment and install dependencies:

   ```powershell
   py -m venv Venv
   .\Venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```

2. Copy `.env.example` to `.env`. Set a unique `DJANGO_SECRET_KEY` of at
   least 32 bytes and configure the database variables. Keep `.env` private
   and never commit it.

   ```powershell
   Copy-Item .env.example .env
   ```

   MySQL is the default. Create the database named by `DB_NAME` before
   migrating. Set `DB_ENGINE=sqlite` to use SQLite for local development.

3. Apply migrations and create an administrator:

   ```powershell
   python manage.py migrate
   python manage.py createsuperuser
   ```

   Assign roles to accounts as needed:

   ```powershell
   python manage.py assign_role USERNAME Administrator
   python manage.py assign_role USERNAME Support
   python manage.py assign_role USERNAME Customer
   ```

   New registrations are assigned the Customer role.

4. Start Django and FastAPI in separate terminals:

   ```powershell
   python manage.py runserver 127.0.0.1:8000
   python -m uvicorn payment_api.main:app --reload --port 8001
   ```

5. Open `http://127.0.0.1:8000/admin/` for the admin panel, or use the web
   pages at `/api/auth/web/login/` and `/cards/`.

Set `DJANGO_DEBUG=False` and configure `DJANGO_ALLOWED_HOSTS` appropriately
outside local development. This simulator is not a production payment
processor.

## Environment variables

| Variable | Purpose |
| --- | --- |
| `DJANGO_SECRET_KEY` | Django and FastAPI JWT signing secret |
| `DJANGO_DEBUG` | Debug mode; use `False` outside development |
| `DJANGO_ALLOWED_HOSTS` | Comma-separated Django host names |
| `DB_ENGINE` | `mysql` (default) or `sqlite` |
| `DB_NAME` | Database name or SQLite file path |
| `DB_USER`, `DB_PASSWORD` | MySQL credentials |
| `DB_HOST`, `DB_PORT` | MySQL host and port |

## Database schema

Django migrations create the built-in authentication/session tables and
`cards_card`. FastAPI's SQLAlchemy metadata creates the `payments` and
`transactions` tables when absent. Django's unmanaged
`transactions.Transaction` model maps to FastAPI's `transactions` table, so
both services share one transaction history.

| Table | Important data |
| --- | --- |
| `auth_user`, `auth_group`, `auth_user_groups` | Accounts, active/admin flags, roles |
| `cards_card` | Owner, type/holder, masked number, last four, expiry |
| `payments` | Payment ID, owner/card IDs, last four, amount, status, time |
| `transactions` | Transaction/payment IDs, owner/card IDs, last four, amount, status, time |

Card number and CVV are write-only card-creation inputs and are discarded by
the serializer. Only the masked number, last four digits, and expiry are
persisted. Payment requests use the saved card ID and last four digits.

## API documentation

Interactive FastAPI documentation:

- [FastAPI Swagger UI](http://127.0.0.1:8001/docs)
- [FastAPI ReDoc](http://127.0.0.1:8001/redoc)
- [FastAPI OpenAPI schema](http://127.0.0.1:8001/openapi.json)

Django REST endpoints are browsable in a browser. The
[Django REST framework API guide](https://www.django-rest-framework.org/api-guide/)
describes the framework behavior used by the following endpoints.

### Django API (`http://127.0.0.1:8000`)

| Method | Path | Purpose |
| --- | --- | --- |
| `POST` | `/api/auth/register/` | Register a Customer and issue JWTs |
| `POST` | `/api/auth/login/` | Obtain a JWT pair |
| `POST` | `/api/auth/refresh/` | Refresh an access token |
| `POST` | `/api/auth/logout/` | Blacklist the caller's refresh token |
| `GET` | `/api/auth/profile/` | Get the authenticated profile |
| `GET`, `POST` | `/api/cards/` | List or add the caller's cards |
| `DELETE` | `/api/cards/delete/{card_id}/` | Delete an owned card after password confirmation |
| `GET` | `/api/transactions/` | List own transactions; filter by status, amount, and date |
| `GET` | `/api/transactions/export/` | Export the caller's filtered transactions as CSV |

### FastAPI payment service (`http://127.0.0.1:8001`)

| Method | Path | Purpose |
| --- | --- | --- |
| `POST` | `/api/auth/login/` | OAuth2 form login for Swagger (`username`, `password`) |
| `GET` | `/api/payments/cards/` | List the authenticated user's saved cards |
| `GET` | `/api/payments/cards/{user_id}` | List cards only when `{user_id}` is the caller |
| `POST` | `/api/payments/` | Simulate a payment |
| `GET` | `/api/payments/{payment_id}` | Get the caller's payment status |

Use the Django-issued access token in an Authorization header with the Bearer
scheme. FastAPI verifies the same Django-signed JWT and checks that the
account is active and has a permitted role. Customer card, payment, and
transaction reads are scoped to the authenticated owner.

## Payment flow

1. Add a card via `POST /api/cards/` and keep its returned `id` and
   `last_four`. Use only dummy card details.
2. Send a payment request to FastAPI:

   ```json
   {
     "card_id": 1,
     "card_last_four": "4242",
     "amount": "35.50",
     "simulate_failure": false
   }
   ```

3. The service validates card ownership and amount, commits a `PENDING`
   payment and transaction, then finalizes both as `SUCCESS` or `FAILED`.
   Set `simulate_failure` to `true`, or select **Simulate a declined payment**
   on the local payment page, to reproduce a decline. The API field is
   optional and defaults to `false`.
4. Verify the result with `GET /api/payments/{payment_id}` and
   `GET /api/transactions/`.

The decline option is a deterministic local test feature, not issuer
authorization behavior. Responses state that no money was charged.

## Roles and administration

- **Administrator:** full Django admin access, role management, payment
  summary, and transaction CSV export.
- **Support:** read-only card and transaction review in the admin.
- **Customer:** access to their own cards, payments, and transactions.

The admin dashboard provides `/admin/payment-summary/` and
`/admin/transactions/export/`. The customer CSV at
`/api/transactions/export/` remains owner-scoped.

## Postman

Import [`postman/Credit-Card-Payment-System.postman_collection.json`](postman/Credit-Card-Payment-System.postman_collection.json).
Set `username` and `password` to a Customer test account, then run the
customer requests in order: login, card creation, payment success/decline,
payment lookup, and transaction filtering/export. The collection saves JWTs,
card IDs, and payment IDs for subsequent requests. Set `admin_username` and
`admin_password` to an Administrator account to run the separate admin
session folder. Use non-production credentials and card data only.

## Tests and coverage

The latest complete run passed **51 tests** at **79% combined statement and
branch coverage**. Run the suite and regenerate the committed coverage report:

```powershell
python manage.py test authentication cards transactions payment_api.tests
python -m coverage run --data-file=.coverage.report manage.py test authentication cards transactions payment_api.tests
python -m coverage report --data-file=.coverage.report --fail-under=50 | Tee-Object reports/coverage-report.txt
```

The generated report is [`reports/coverage-report.txt`](reports/coverage-report.txt).

## Screenshots

The screenshots below were captured from the local services using temporary
test data. They contain no real credentials, card numbers, or CVVs.

- [FastAPI Swagger UI](screenshots/fastapi-swagger.png)
- [Successful simulated payment](screenshots/payment-success.png)
- [Declined simulated payment](screenshots/payment-failed.png)
- [Customer transaction history](screenshots/transaction-history.png)
- [Django admin panel](screenshots/admin-panel.png)
