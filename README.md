# Credit Card

Django provides account registration and JWT authentication, user-owned cards
and transaction history, and a staff-only administration panel. The separate
FastAPI payment service uses the same Django database and signing key.

## Setup

1. Create and activate a virtual environment, then install all dependencies
   with `pip install -r requirements.txt`.
2. Copy `.env.example` to `.env` and replace `DJANGO_SECRET_KEY` with a
   randomly generated secret. Keep `.env` private and out of source control.
   MySQL is the default database. Set `DB_NAME`, `DB_USER`, `DB_PASSWORD`,
   `DB_HOST`, and `DB_PORT` to the connection details used by MySQL Workbench.
3. Initialize Django's database and create an administrator:

   ```powershell
   .\Venv\Scripts\python.exe manage.py migrate
   .\Venv\Scripts\python.exe manage.py createsuperuser
   ```

   Assign roles to existing accounts with an administrator account. Supported
   roles are `Administrator`, `Support`, and `Customer`:

   ```powershell
   .\Venv\Scripts\python.exe manage.py assign_role USERNAME Administrator
   .\Venv\Scripts\python.exe manage.py assign_role USERNAME Support
   .\Venv\Scripts\python.exe manage.py assign_role USERNAME Customer
   ```

4. Start the Django site and payment API in separate terminals:

   ```powershell
   .\Venv\Scripts\python.exe manage.py runserver
   .\Venv\Scripts\python.exe -m uvicorn payment_api.main:app --reload --port 8001
   ```

Set `DJANGO_ALLOWED_HOSTS` to the hosts used in the deployment and keep
`DJANGO_DEBUG=False` outside local development.

## Admin panel

Application roles use Django groups. Administrators can manage users, roles,
cards, and transactions in `/admin/`; Support can only review cards and
transactions; Customers can access only their own cards, transactions, and
payments outside the admin. New registrations are assigned the Customer role.
Sign in to `/admin/` with an Administrator or Support account. The admin
dashboard links to
`/admin/payment-summary/` for today's transaction counts and successful payment
amount, and `/admin/transactions/export/` downloads all transaction records as
a CSV. Summary views, CSV exports, and standard Django admin edits are recorded
in the admin activity log.

The separate user transaction CSV at `/api/transactions/export/` is scoped to
the signed-in user. It is not the administrator export.

## API and payment security

- Obtain and refresh JWTs at `/api/auth/login/` and `/api/auth/refresh/`.
  Protected Django REST endpoints use JWT authentication.
- The FastAPI service also exposes `/api/auth/login/` as an OAuth2 form
  endpoint for the Swagger Authorize button. It accepts `username` and
  `password` as form fields and issues access tokens signed with the same
  Django secret. Django REST login remains available at `/api/auth/login/` on
  the Django server and accepts JSON. Send either issued access token to
  protected payment endpoints as `Authorization: Bearer <access-token>`.
- Protected FastAPI payment routes declare OAuth2 Password Bearer security in
  the API schema and accept the same JWT access token in the
  `Authorization: Bearer <access-token>` header. The token is still issued by
  Django's `/api/auth/login/` endpoint.
- Cards and transactions are always filtered by the authenticated owner.
  The FastAPI payment API requires the same bearer access token and derives the
  account ID from that token rather than trusting a request-supplied user ID.
- Card input is validated before persistence. Only a masked number, last four
  digits, and expiry are saved; the submitted full number and CVV are never
  stored or returned.
- SQL values use Django ORM or SQLAlchemy bound parameters.
- The payment API is a local simulation, not a payment processor. It accepts
  the signed-in user's saved `card_id`, the card's `card_last_four`, and the
  amount. It rejects cards not owned by that user and last-four values that do
  not match. A valid request creates a successful payment and transaction
  record for testing; no money is charged and no full card number or CVV is
  collected.
- The `payment_id` for simulated payments starts with `SIM-PAY-`. Swagger's
  `POST /api/payments/` response explicitly says that no real money was
  charged. Razorpay credentials are not required.

## Tests and coverage

Run the complete Django, card, transaction, and payment-service tests:

```powershell
.\Venv\Scripts\python.exe manage.py test authentication cards transactions payment_api.tests
```

Enforce the 50% line-and-branch coverage threshold:

```powershell
.\Venv\Scripts\python.exe -m coverage run manage.py test authentication cards transactions payment_api.tests
.\Venv\Scripts\python.exe -m coverage report
```
