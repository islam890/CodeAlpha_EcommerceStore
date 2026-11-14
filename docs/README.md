# Project Documentation

## Runtime and architecture

This project is a server-rendered Django 5.2.19 e-commerce store using the
built-in Django `User` model, a separate `Profile`, Django templates, Bootstrap
5, and SQLite for local development. PostgreSQL is supported through the
environment-driven Django database configuration.

The applications are intentionally separated by responsibility:

- `accounts`: registration, authentication, profiles, and password workflows.
- `catalog`: categories, products, image validation, search, filtering, and
  product details.
- `cart`: authenticated and session carts, quantity changes, and cart totals.
- `orders`: checkout, order snapshots, cancellation, and order history.
- `reviews`: review submission, moderation visibility, editing, and deletion.
- `wishlist`: user-owned saved products.
- `dashboard`: staff-only read-only statistics and management listings.

## Data and transaction notes

Checkout recalculates prices from database products, validates stock, creates
historical `OrderItem` snapshots, decrements stock, and clears the cart inside
one transaction. Cash on Delivery is the only supported payment method; no
payment gateway is integrated.

SQLite is suitable for development but does not provide production-grade
row-level locking for concurrent checkout or cancellation. Use PostgreSQL or
another transactional production database before accepting concurrent
traffic.

## Database configuration

SQLite remains the default when `DJANGO_DB_ENGINE` is unset or set to
`sqlite`. PostgreSQL can be selected with `DJANGO_DB_ENGINE=postgresql`.
PostgreSQL requires `DJANGO_DB_NAME`, `DJANGO_DB_USER`, and
`DJANGO_DB_HOST`; `DJANGO_DB_PASSWORD` may be empty when the server
authentication configuration does not require one. `DJANGO_DB_PORT` defaults
to `5432`, `DJANGO_DB_CONN_MAX_AGE` defaults to `0`, and `DJANGO_DB_SSLMODE`
is optional.

Invalid PostgreSQL configuration fails during startup and never falls back to
SQLite. To initialize a newly created PostgreSQL database, configure the
variables and run `python manage.py migrate`.

## Email configuration

Development uses Django's console email backend by default. Password-reset
messages are printed to the development console and are not sent externally.
Production uses SMTP and fails closed unless an SMTP host and valid default
sender address are configured.

Configure `DJANGO_EMAIL_BACKEND`, `DJANGO_EMAIL_HOST`,
`DJANGO_EMAIL_PORT`, `DJANGO_EMAIL_USE_TLS`, `DJANGO_EMAIL_USE_SSL`,
`DJANGO_EMAIL_HOST_USER`, `DJANGO_EMAIL_HOST_PASSWORD`,
`DJANGO_EMAIL_TIMEOUT`, and `DJANGO_DEFAULT_FROM_EMAIL` as needed.
TLS and SSL cannot both be enabled. Username and password must be supplied
together. Never commit real SMTP credentials.

## Production configuration

Set `DJANGO_ENV=production`, a real `DJANGO_SECRET_KEY`,
`DJANGO_DEBUG=False`, explicit `DJANGO_ALLOWED_HOSTS`, and the HTTPS-related
variables documented in `.env.example`. The application fails closed unless
HTTPS redirect, secure session and CSRF cookies, and positive HSTS seconds are
configured. Production should also use HTTPS, a production database, managed
static/media storage, and appropriate backups and monitoring.

Orders may transition from pending to processing, processing to shipped,
shipped to delivered, or pending/processing to cancelled. Payment status
transitions are pending to paid/failed, failed back to pending, and paid to
refunded. SQLite remains suitable only for development because it does not
provide production-grade row-level checkout locking.

Order and payment transitions should use the order services. The database
enforces order totals and order-item line totals with check constraints, while
unrestricted internal ORM code can still bypass transition policy because
database rows cannot express previous-value transition rules.

## Current limitations

- Staff product and order pages display real querysets but do not provide CRUD
  forms; use Django admin for management.
- Newsletter markup is presentational only and has no subscription service.
- Cash on Delivery is the only payment method.
