# Project Documentation

## Runtime and architecture

This project is a server-rendered Django 5.2.19 e-commerce store using the
built-in Django `User` model, a separate `Profile`, Django templates, Bootstrap
5, and SQLite for local development.

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
