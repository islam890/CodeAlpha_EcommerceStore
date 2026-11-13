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

Set a real `DJANGO_SECRET_KEY`, `DJANGO_DEBUG=False`, explicit
`DJANGO_ALLOWED_HOSTS`, and the HTTPS-related variables documented in
`.env.example`. Production should also use HTTPS, secure cookies, HSTS after
careful rollout, a production database, managed static/media storage, and
appropriate backups and monitoring.

## Current limitations

- Staff product and order pages display real querysets but do not provide CRUD
  forms; use Django admin for management.
- Newsletter markup is presentational only and has no subscription service.
- Cash on Delivery is the only payment method.
