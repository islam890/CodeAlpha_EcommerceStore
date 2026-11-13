# CodeAlpha E-Commerce Store

Professional server-rendered e-commerce storefront built with Python 3.13,
Django 5.2.19, Django Templates, Bootstrap 5, CSS, and JavaScript.

## Features

- Registration, login, logout, password reset, password change, and profiles.
- Active product catalog with categories, search, filtering, sorting, and
  pagination.
- Authenticated and guest shopping carts with stock validation.
- Wishlist management with user ownership.
- Checkout with server-calculated totals, shipping fees, Cash on Delivery, and
  historical order-item pricing.
- Order history, detail views, status display, and authorized cancellation.
- Moderated product reviews with owner-only edit/delete.
- Staff-only statistics and query-backed product/order listings.
- Responsive Luma & Co. templates with reusable navigation, cards, messages,
  forms, and empty states.

## Technology stack

- Python 3.13
- Django 5.2.19
- SQLite for development; PostgreSQL-compatible ORM design
- Django ORM, Forms, Authentication, and CSRF middleware
- Django Templates, Bootstrap 5, CSS3, and JavaScript

## Prerequisites and setup

PowerShell:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Configure `.env` before deployment. Never commit real secrets.
When `DJANGO_DEBUG=False`, the application refuses to start without
`DJANGO_SECRET_KEY`.

## Database

For a fresh development database:

```powershell
python manage.py migrate
python manage.py createsuperuser
```

Existing development data must not be reset or recreated. Migrations are
preserved in each application.

## Run the application

```powershell
python manage.py check
python manage.py runserver
```

Open `http://127.0.0.1:8000/`.

## Tests and verification

```powershell
python manage.py test
python manage.py makemigrations --check --dry-run
python manage.py migrate --check
python manage.py check --deploy
```

`check --deploy` reports warnings when local HTTP development defaults are
active. Configure the HTTPS-related environment variables for production
instead of enabling them blindly during local development.

## Main URLs

- `/` — storefront homepage
- `/catalog/products/` — product catalog
- `/catalog/categories/` — categories
- `/catalog/search/` — search
- `/cart/` — shopping cart
- `/wishlist/` — authenticated wishlist
- `/orders/checkout/` — checkout
- `/orders/history/` — authenticated order history
- `/accounts/profile/` — authenticated account dashboard
- `/dashboard/` — staff-only dashboard
- `/admin/` — Django admin

## Staff access

Create a superuser or staff user with `createsuperuser`. Dashboard access is
restricted to authenticated users with `is_staff=True`. Product and order
management pages are currently read-only listings; use Django admin for CRUD.

## Limitations and production requirements

- Cash on Delivery is the only payment method. No real payment gateway exists.
- SQLite does not provide production-grade concurrent row locking; use
  PostgreSQL for production checkout traffic.
- Newsletter markup is presentational and has no subscription backend.
- Configure a real secret key, `DEBUG=False`, explicit allowed hosts, HTTPS,
  secure cookies, HSTS, production static/media storage, backups, and
  monitoring before deployment.

More implementation notes are in [`docs/README.md`](docs/README.md).
