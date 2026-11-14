from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth.models import User
from django.contrib import admin as django_admin
from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, transaction
from django.test import Client
from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import Profile
from apps.catalog.models import Category, Product
from apps.cart.models import Cart, CartItem
from apps.cart.services import add_item, merge_carts
from apps.dashboard.selectors import dashboard_stats, sales_summary
from apps.orders.admin import OrderAdmin, OrderAdminForm
from apps.orders.models import Order, OrderItem
from apps.orders.services import (
    cancel_order,
    create_order,
    transition_order_status,
    transition_payment_status,
)
from apps.reviews.models import Review
from apps.wishlist.models import Wishlist, WishlistItem
from config.settings import (
    DEVELOPMENT_SECRET_KEY,
    get_database_config,
    parse_allowed_hosts,
    validate_production_security,
    validate_production_configuration,
)


class BackendWorkflowTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="alex",
            password="Correct-password-123",
            email="alex@example.com",
        )
        self.other_user = User.objects.create_user(username="other", password="Correct-password-123")
        self.category = Category.objects.create(name="Essentials", slug="essentials")
        self.product = Product.objects.create(
            category=self.category,
            name="Daily Mug",
            slug="daily-mug",
            sku="MUG-001",
            description="A useful mug.",
            price=Decimal("32.00"),
            stock_quantity=5,
        )

    def test_profile_created_for_new_user(self):
        self.assertTrue(Profile.objects.filter(user=self.user).exists())

    def test_production_configuration_rejects_unsafe_values(self):
        with self.assertRaises(ImproperlyConfigured):
            validate_production_configuration(
                environment="production",
                debug=True,
                secret_key="real-secret",
                allowed_hosts=["shop.example"],
            )
        with self.assertRaises(ImproperlyConfigured):
            validate_production_configuration(
                environment="production",
                debug=False,
                secret_key=None,
                allowed_hosts=["shop.example"],
            )
        with self.assertRaises(ImproperlyConfigured):
            validate_production_configuration(
                environment="production",
                debug=False,
                secret_key=DEVELOPMENT_SECRET_KEY,
                allowed_hosts=["shop.example"],
            )
        with self.assertRaises(ImproperlyConfigured):
            validate_production_configuration(
                environment="production",
                debug=False,
                secret_key="replace-this-development-secret",
                allowed_hosts=["shop.example"],
            )
        with self.assertRaises(ImproperlyConfigured):
            validate_production_configuration(
                environment="production",
                debug=False,
                secret_key="a" * 60,
                allowed_hosts=["127.0.0.1", "localhost"],
                allowed_hosts_configured=False,
            )
        for raw_hosts in ("   ", ",,,"):
            self.assertEqual(parse_allowed_hosts(raw_hosts), [])
            with self.assertRaises(ImproperlyConfigured):
                validate_production_configuration(
                    environment="production",
                    debug=False,
                    secret_key="a" * 60,
                    allowed_hosts=parse_allowed_hosts(raw_hosts),
                )
        self.assertEqual(
            parse_allowed_hosts(" shop.example , api.shop.example "),
            ["shop.example", "api.shop.example"],
        )

    def test_production_configuration_requires_https_security(self):
        secure_values = {
            "environment": "production",
            "secure_ssl_redirect": True,
            "session_cookie_secure": True,
            "csrf_cookie_secure": True,
            "hsts_seconds": 31536000,
        }
        validate_production_security(**secure_values)
        for setting in (
            "secure_ssl_redirect",
            "session_cookie_secure",
            "csrf_cookie_secure",
        ):
            with self.assertRaises(ImproperlyConfigured):
                validate_production_security(**{**secure_values, setting: False})
        with self.assertRaises(ImproperlyConfigured):
            validate_production_security(**{**secure_values, "hsts_seconds": 0})

    def test_database_configuration_defaults_to_sqlite(self):
        config = get_database_config({})
        self.assertEqual(config["ENGINE"], "django.db.backends.sqlite3")
        self.assertTrue(str(config["NAME"]).endswith("db.sqlite3"))

    def test_database_configuration_rejects_unknown_engine(self):
        with self.assertRaisesRegex(
            ImproperlyConfigured,
            "DJANGO_DB_ENGINE must be sqlite or postgresql",
        ):
            get_database_config({"DJANGO_DB_ENGINE": "mysql"})

    def test_database_configuration_supports_postgresql(self):
        config = get_database_config(
            {
                "DJANGO_DB_ENGINE": "postgresql",
                "DJANGO_DB_NAME": "codealpha_store",
                "DJANGO_DB_USER": "codealpha",
                "DJANGO_DB_PASSWORD": "not-a-real-password",
                "DJANGO_DB_HOST": "127.0.0.1",
                "DJANGO_DB_PORT": "5433",
                "DJANGO_DB_CONN_MAX_AGE": "60",
                "DJANGO_DB_SSLMODE": "require",
            }
        )
        self.assertEqual(config["ENGINE"], "django.db.backends.postgresql")
        self.assertEqual(config["NAME"], "codealpha_store")
        self.assertEqual(config["USER"], "codealpha")
        self.assertEqual(config["PORT"], "5433")
        self.assertEqual(config["CONN_MAX_AGE"], 60)
        self.assertEqual(config["OPTIONS"], {"sslmode": "require"})
        self.assertEqual(
            get_database_config(
                {
                    "DJANGO_DB_ENGINE": "postgresql",
                    "DJANGO_DB_NAME": "codealpha_store",
                    "DJANGO_DB_USER": "codealpha",
                    "DJANGO_DB_HOST": "127.0.0.1",
                }
            )["OPTIONS"],
            {},
        )

    def test_database_configuration_uses_postgresql_defaults(self):
        config = get_database_config(
            {
                "DJANGO_DB_ENGINE": "postgresql",
                "DJANGO_DB_NAME": "codealpha_store",
                "DJANGO_DB_USER": "codealpha",
                "DJANGO_DB_HOST": "127.0.0.1",
            }
        )
        self.assertEqual(config["PORT"], "5432")
        self.assertEqual(config["CONN_MAX_AGE"], 0)

    def test_database_configuration_rejects_incomplete_postgresql(self):
        base = {
            "DJANGO_DB_ENGINE": "postgresql",
            "DJANGO_DB_NAME": "codealpha_store",
            "DJANGO_DB_USER": "codealpha",
            "DJANGO_DB_HOST": "127.0.0.1",
        }
        for missing in ("DJANGO_DB_NAME", "DJANGO_DB_USER", "DJANGO_DB_HOST"):
            invalid = {**base, missing: ""}
            with self.assertRaises(ImproperlyConfigured):
                get_database_config(invalid)

    def test_database_configuration_rejects_whitespace_required_values(self):
        base = {
            "DJANGO_DB_ENGINE": "postgresql",
            "DJANGO_DB_NAME": "codealpha_store",
            "DJANGO_DB_USER": "codealpha",
            "DJANGO_DB_HOST": "127.0.0.1",
        }
        for required in ("DJANGO_DB_NAME", "DJANGO_DB_USER", "DJANGO_DB_HOST"):
            with self.assertRaises(ImproperlyConfigured):
                get_database_config({**base, required: "   "})

    def test_database_configuration_rejects_invalid_numeric_values(self):
        base = {
            "DJANGO_DB_ENGINE": "postgresql",
            "DJANGO_DB_NAME": "codealpha_store",
            "DJANGO_DB_USER": "codealpha",
            "DJANGO_DB_HOST": "127.0.0.1",
        }
        with self.assertRaises(ImproperlyConfigured):
            get_database_config({**base, "DJANGO_DB_CONN_MAX_AGE": "-1"})
        with self.assertRaises(ImproperlyConfigured):
            get_database_config({**base, "DJANGO_DB_PORT": "not-a-port"})

    def test_database_configuration_rejects_non_numeric_connection_age(self):
        base = {
            "DJANGO_DB_ENGINE": "postgresql",
            "DJANGO_DB_NAME": "codealpha_store",
            "DJANGO_DB_USER": "codealpha",
            "DJANGO_DB_HOST": "127.0.0.1",
        }
        with self.assertRaisesRegex(
            ImproperlyConfigured,
            "DJANGO_DB_CONN_MAX_AGE must be an integer",
        ):
            get_database_config({**base, "DJANGO_DB_CONN_MAX_AGE": "persistent"})

    def test_registration_and_login(self):
        response = self.client.post(
            reverse("accounts:register"),
            {
                "first_name": "New",
                "last_name": "Customer",
                "username": "new-customer",
                "email": "new@example.com",
                "password1": "Strong-password-123",
                "password2": "Strong-password-123",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(self.client.login(username="new-customer", password="Strong-password-123"))

    def test_product_price_and_stock_validation(self):
        self.product.price = Decimal("-1.00")
        with self.assertRaises(ValidationError):
            self.product.full_clean()

    def test_inactive_products_are_not_publicly_listed(self):
        self.product.is_active = False
        self.product.save(update_fields=("is_active",))
        response = self.client.get(reverse("catalog:products"))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, self.product.name)
        self.product.price = Decimal("1.00")
        self.product.stock_quantity = -1
        with self.assertRaises(ValidationError):
            self.product.full_clean()

    def test_cart_prevents_duplicate_and_calculates_total(self):
        cart = Cart.objects.create(user=self.user)
        add_item(cart, self.product, 2)
        add_item(cart, self.product, 1)
        self.assertEqual(cart.items.count(), 1)
        self.assertEqual(cart.items.get().quantity, 3)
        self.assertEqual(cart.items.get().line_total, Decimal("96.00"))
        self.assertEqual(cart.subtotal, Decimal("96.00"))

    def test_cart_rejects_quantity_above_stock(self):
        cart = Cart.objects.create(user=self.user)
        with self.assertRaises(ValueError):
            add_item(cart, self.product, 6)

    def test_wishlist_duplicate_prevention_and_ownership(self):
        wishlist = Wishlist.objects.create(user=self.user)
        WishlistItem.objects.create(wishlist=wishlist, product=self.product)
        WishlistItem.objects.get_or_create(wishlist=wishlist, product=self.product)
        self.assertEqual(wishlist.items.count(), 1)
        self.client.force_login(self.other_user)
        response = self.client.get(reverse("wishlist:detail"))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, self.product.name)

    def test_order_snapshots_price_and_reduces_stock(self):
        cart = Cart.objects.create(user=self.user)
        add_item(cart, self.product, 2)
        order = create_order(
            user=self.user,
            cart=cart,
            checkout_data={
                "shipping_name": "Alex Customer",
                "shipping_email": "alex@example.com",
                "shipping_phone": "",
                "shipping_address": "123 Main Street",
                "payment_method": Order.PaymentMethod.COD,
            },
        )
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 3)
        self.assertEqual(order.subtotal, Decimal("64.00"))
        self.assertEqual(order.total, Decimal("64.00") + Decimal("8.00"))
        self.assertEqual(order.items.get().unit_price, Decimal("32.00"))
        self.product.price = Decimal("40.00")
        self.product.save()
        self.assertEqual(order.items.get().unit_price, Decimal("32.00"))

    def test_checkout_updates_stock_for_each_locked_product(self):
        second_product = Product.objects.create(
            category=self.category,
            name="Daily Plate",
            slug="daily-plate",
            sku="PLATE-001",
            description="A useful plate.",
            price=Decimal("18.00"),
            stock_quantity=4,
        )
        cart = Cart.objects.create(user=self.user)
        add_item(cart, self.product, 2)
        add_item(cart, second_product, 3)

        order = create_order(
            user=self.user,
            cart=cart,
            checkout_data={
                "shipping_name": "Alex Customer",
                "shipping_email": "alex@example.com",
                "shipping_phone": "",
                "shipping_address": "123 Main Street",
                "payment_method": Order.PaymentMethod.COD,
            },
        )

        self.product.refresh_from_db()
        second_product.refresh_from_db()
        self.assertEqual(order.items.count(), 2)
        self.assertEqual(self.product.stock_quantity, 3)
        self.assertEqual(second_product.stock_quantity, 1)

    def test_checkout_preserves_two_decimal_money_totals(self):
        self.product.price = Decimal("12.34")
        self.product.save(update_fields=("price",))
        cart = Cart.objects.create(user=self.user)
        add_item(cart, self.product, 3)
        order = create_order(
            user=self.user,
            cart=cart,
            checkout_data={
                "shipping_name": "Alex Customer",
                "shipping_email": "alex@example.com",
                "shipping_phone": "",
                "shipping_address": "123 Main Street",
                "payment_method": Order.PaymentMethod.COD,
            },
        )
        self.assertEqual(order.subtotal, Decimal("37.02"))
        self.assertEqual(order.total, Decimal("45.02"))
        self.assertEqual(order.items.get().line_total, Decimal("37.02"))

    def test_order_totals_and_status_transitions_are_validated(self):
        order = Order(
            order_number="LM-INVALID-TOTAL",
            user=self.user,
            subtotal=Decimal("10.00"),
            shipping_fee=Decimal("8.00"),
            total=Decimal("10.00"),
            shipping_name="Alex",
            shipping_email="alex@example.com",
            shipping_address="123 Main Street",
        )
        with self.assertRaises(ValidationError):
            order.full_clean()

        self.assertTrue(Order.is_valid_status_transition(Order.Status.PENDING, Order.Status.PROCESSING))
        self.assertFalse(Order.is_valid_status_transition(Order.Status.DELIVERED, Order.Status.PROCESSING))
        self.assertTrue(Order.is_valid_payment_transition(Order.PaymentStatus.PAID, Order.PaymentStatus.REFUNDED))
        self.assertFalse(Order.is_valid_payment_transition(Order.PaymentStatus.REFUNDED, Order.PaymentStatus.PAID))

        existing = Order.objects.create(
            order_number="LM-ADMIN-TRANSITION",
            user=self.user,
            status=Order.Status.PROCESSING,
            subtotal=Decimal("10.00"),
            shipping_fee=Decimal("0.00"),
            total=Decimal("10.00"),
            shipping_name="Alex",
            shipping_email="alex@example.com",
            shipping_address="123 Main Street",
        )
        form = OrderAdminForm(
            instance=existing,
            data={
                "user": self.user.pk,
                "status": Order.Status.PENDING,
                "payment_method": Order.PaymentMethod.COD,
                "payment_status": Order.PaymentStatus.PENDING,
                "subtotal": "10.00",
                "shipping_fee": "0.00",
                "total": "10.00",
                "shipping_name": "Alex",
                "shipping_email": "alex@example.com",
                "shipping_phone": "",
                "shipping_address": "123 Main Street",
            },
        )
        self.assertFalse(form.is_valid())
        self.assertIn("status", form.errors)

    def test_database_constraints_reject_invalid_financial_records(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Order.objects.create(
                    order_number="LM-CONSTRAINT-ORDER",
                    user=self.user,
                    subtotal=Decimal("10.00"),
                    shipping_fee=Decimal("8.00"),
                    total=Decimal("1.00"),
                    shipping_name="Alex",
                    shipping_email="alex@example.com",
                    shipping_address="123 Main Street",
                )

        order = Order.objects.create(
            order_number="LM-CONSTRAINT-ITEM",
            user=self.user,
            subtotal=Decimal("20.00"),
            shipping_fee=Decimal("0.00"),
            total=Decimal("20.00"),
            shipping_name="Alex",
            shipping_email="alex@example.com",
            shipping_address="123 Main Street",
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                OrderItem.objects.create(
                    order=order,
                    product=self.product,
                    product_name=self.product.name,
                    sku=self.product.sku,
                    unit_price=Decimal("10.00"),
                    quantity=2,
                    line_total=Decimal("1.00"),
                )

        item = OrderItem.objects.create(
            order=order,
            product=self.product,
            product_name=self.product.name,
            sku=self.product.sku,
            unit_price=Decimal("10.00"),
            quantity=2,
            line_total=Decimal("20.00"),
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Order.objects.filter(pk=order.pk).update(total=Decimal("1.00"))
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                OrderItem.objects.filter(pk=item.pk).update(line_total=Decimal("1.00"))

    def test_order_transitions_use_service_and_admin_paths(self):
        order = Order.objects.create(
            order_number="LM-SERVICE-TRANSITION",
            user=self.user,
            subtotal=Decimal("10.00"),
            shipping_fee=Decimal("0.00"),
            total=Decimal("10.00"),
            shipping_name="Alex",
            shipping_email="alex@example.com",
            shipping_address="123 Main Street",
        )
        transition_order_status(order, Order.Status.PROCESSING)
        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.PROCESSING)
        with self.assertRaises(ValueError):
            transition_order_status(order, Order.Status.PENDING)
        transition_payment_status(order, Order.PaymentStatus.PAID)
        order.refresh_from_db()
        self.assertEqual(order.payment_status, Order.PaymentStatus.PAID)
        with self.assertRaises(ValueError):
            transition_payment_status(order, Order.PaymentStatus.PENDING)

        order.status = Order.Status.SHIPPED
        OrderAdmin(Order, django_admin.site).save_model(None, order, None, True)
        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.SHIPPED)

    def test_order_rejects_insufficient_stock_and_cancellation_restores(self):
        cart = Cart.objects.create(user=self.user)
        add_item(cart, self.product, 2)
        order = create_order(
            user=self.user,
            cart=cart,
            checkout_data={
                "shipping_name": "Alex Customer",
                "shipping_email": "alex@example.com",
                "shipping_phone": "",
                "shipping_address": "123 Main Street",
                "payment_method": Order.PaymentMethod.COD,
            },
        )
        cancel_order(order)
        self.product.refresh_from_db()
        self.assertEqual(order.status, Order.Status.CANCELLED)
        self.assertEqual(self.product.stock_quantity, 5)
        second_cart = Cart.objects.create(user=self.other_user)
        CartItem.objects.create(cart=second_cart, product=self.product, quantity=6)
        with self.assertRaises(ValueError):
            create_order(
                user=self.other_user,
                cart=second_cart,
                checkout_data={
                    "shipping_name": "Other Customer",
                    "shipping_email": "other@example.com",
                    "shipping_phone": "",
                    "shipping_address": "456 Main Street",
                    "payment_method": Order.PaymentMethod.COD,
                },
            )

        with self.assertRaises(ValueError):
            cancel_order(order)

    def test_insufficient_stock_rolls_back_order_and_cart(self):
        cart = Cart.objects.create(user=self.other_user)
        CartItem.objects.create(cart=cart, product=self.product, quantity=6)

        with self.assertRaisesMessage(ValueError, "does not have enough stock"):
            create_order(
                user=self.other_user,
                cart=cart,
                checkout_data={
                    "shipping_name": "Other Customer",
                    "shipping_email": "other@example.com",
                    "shipping_phone": "",
                    "shipping_address": "456 Main Street",
                    "payment_method": Order.PaymentMethod.COD,
                },
            )

        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 5)
        self.assertFalse(Order.objects.filter(user=self.other_user).exists())
        self.assertTrue(CartItem.objects.filter(cart=cart).exists())

    def test_cancellation_restores_stock_for_each_product(self):
        second_product = Product.objects.create(
            category=self.category,
            name="Daily Plate",
            slug="daily-plate-cancel",
            sku="PLATE-CANCEL-001",
            description="A useful plate.",
            price=Decimal("18.00"),
            stock_quantity=4,
        )
        cart = Cart.objects.create(user=self.user)
        add_item(cart, self.product, 2)
        add_item(cart, second_product, 3)
        order = create_order(
            user=self.user,
            cart=cart,
            checkout_data={
                "shipping_name": "Alex Customer",
                "shipping_email": "alex@example.com",
                "shipping_phone": "",
                "shipping_address": "123 Main Street",
                "payment_method": Order.PaymentMethod.COD,
            },
        )

        cancel_order(order)

        self.product.refresh_from_db()
        second_product.refresh_from_db()
        self.assertEqual(order.status, Order.Status.CANCELLED)
        self.assertEqual(self.product.stock_quantity, 5)
        self.assertEqual(second_product.stock_quantity, 4)

    def test_anonymous_and_non_owner_cannot_cancel_order(self):
        order = Order.objects.create(
            order_number="LM-CANCEL-001",
            user=self.user,
            subtotal=Decimal("10.00"),
            shipping_fee=Decimal("0.00"),
            total=Decimal("10.00"),
            shipping_name="Alex",
            shipping_email="alex@example.com",
            shipping_address="123 Main Street",
        )
        response = self.client.post(reverse("orders:cancel", args=[order.order_number]))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("accounts:login"), response.url)
        self.client.force_login(self.other_user)
        response = self.client.post(reverse("orders:cancel", args=[order.order_number]))
        self.assertEqual(response.status_code, 404)
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.user)
        response = csrf_client.post(reverse("orders:cancel", args=[order.order_number]))
        self.assertEqual(response.status_code, 403)

    def test_checkout_without_cart_or_with_empty_cart_is_rejected(self):
        self.client.force_login(self.user)
        checkout_data = {
            "shipping_name": "Alex Customer",
            "shipping_email": "alex@example.com",
            "shipping_phone": "",
            "shipping_address": "123 Main Street",
            "payment_method": Order.PaymentMethod.COD,
        }
        response = self.client.post(reverse("orders:checkout"), checkout_data)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "cart is unavailable")
        Cart.objects.create(user=self.user)
        response = self.client.post(reverse("orders:checkout"), checkout_data)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "cart is empty")
        self.assertEqual(Order.objects.count(), 0)

    def test_sequential_duplicate_checkout_creates_one_order(self):
        cart = Cart.objects.create(user=self.user)
        add_item(cart, self.product, 1)
        checkout_data = {
            "shipping_name": "Alex Customer",
            "shipping_email": "alex@example.com",
            "shipping_phone": "",
            "shipping_address": "123 Main Street",
            "payment_method": Order.PaymentMethod.COD,
        }
        self.client.force_login(self.user)
        first = self.client.post(reverse("orders:checkout"), checkout_data)
        second = self.client.post(reverse("orders:checkout"), checkout_data)
        self.assertEqual(first.status_code, 302)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(Order.objects.filter(user=self.user).count(), 1)

    def test_order_creation_rolls_back_on_failure(self):
        cart = Cart.objects.create(user=self.user)
        add_item(cart, self.product, 1)
        with patch("apps.orders.services.Order.objects.create", side_effect=RuntimeError):
            with self.assertRaises(RuntimeError):
                create_order(
                    user=self.user,
                    cart=cart,
                    checkout_data={
                        "shipping_name": "Alex",
                        "shipping_email": "alex@example.com",
                        "shipping_address": "123 Main Street",
                        "payment_method": Order.PaymentMethod.COD,
                    },
                )
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 5)
        self.assertTrue(CartItem.objects.filter(cart=cart, product=self.product).exists())

    def test_checkout_service_rejects_invalid_internal_input(self):
        cart = Cart.objects.create(user=self.user)
        add_item(cart, self.product, 1)
        checkout_data = {
            "shipping_name": "Alex",
            "shipping_email": "alex@example.com",
            "shipping_address": "123 Main Street",
            "payment_method": "card",
        }
        with self.assertRaisesMessage(ValueError, "payment method"):
            create_order(user=self.user, cart=cart, checkout_data=checkout_data)
        self.assertFalse(Order.objects.exists())
        self.assertTrue(CartItem.objects.filter(cart=cart).exists())
        checkout_data["payment_method"] = Order.PaymentMethod.COD
        checkout_data.pop("shipping_address")
        with self.assertRaisesMessage(ValueError, "Shipping address is required"):
            create_order(user=self.user, cart=cart, checkout_data=checkout_data)

    def test_paid_order_cannot_be_cancelled(self):
        order = Order.objects.create(
            order_number="LM-PAID-001",
            user=self.user,
            subtotal=Decimal("10.00"),
            shipping_fee=Decimal("0.00"),
            total=Decimal("10.00"),
            shipping_name="Alex",
            shipping_email="alex@example.com",
            shipping_address="123 Main Street",
            payment_status=Order.PaymentStatus.PAID,
        )
        with self.assertRaisesMessage(ValueError, "refund workflow"):
            cancel_order(order)
        self.assertEqual(order.status, Order.Status.PENDING)

    def test_order_access_is_limited_to_owner(self):
        order = Order.objects.create(
            order_number="LM-TEST-001",
            user=self.user,
            subtotal=Decimal("10.00"),
            shipping_fee=Decimal("0.00"),
            total=Decimal("10.00"),
            shipping_name="Alex",
            shipping_email="alex@example.com",
            shipping_address="123 Main Street",
        )
        self.client.force_login(self.other_user)
        response = self.client.get(reverse("orders:detail", args=[order.order_number]))
        self.assertEqual(response.status_code, 404)

    def test_review_validation_and_duplicate_constraint(self):
        Review.objects.create(product=self.product, user=self.user, rating=5, title="Great", content="Useful.")
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Review.objects.create(product=self.product, user=self.user, rating=4, title="Again", content="Duplicate.")

        self.client.force_login(self.other_user)
        form_response = self.client.post(
            reverse("reviews:create", args=[self.product.slug]),
            {"rating": 6, "title": "Invalid", "content": "Invalid rating."},
        )
        self.assertEqual(form_response.status_code, 200)

    def test_review_edit_delete_are_owner_only_and_edits_require_moderation(self):
        review = Review.objects.create(
            product=self.product,
            user=self.user,
            rating=5,
            title="Great",
            content="Useful.",
            is_approved=True,
        )
        self.client.force_login(self.other_user)
        self.assertEqual(
            self.client.post(reverse("reviews:edit", args=[review.pk]), {"rating": 4, "title": "No", "content": "No"}).status_code,
            404,
        )
        self.assertEqual(
            self.client.post(reverse("reviews:delete", args=[review.pk])).status_code,
            302,
        )
        self.assertTrue(Review.objects.filter(pk=review.pk).exists())
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("reviews:edit", args=[review.pk]),
            {"rating": 4, "title": "Updated", "content": "Changed."},
        )
        self.assertEqual(response.status_code, 302)
        review.refresh_from_db()
        self.assertFalse(review.is_approved)
        self.client.post(reverse("reviews:delete", args=[review.pk]))
        self.assertFalse(Review.objects.filter(pk=review.pk).exists())

    def test_duplicate_review_submission_returns_form_error(self):
        Review.objects.create(product=self.product, user=self.user, rating=5, title="Great", content="Useful.")
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("reviews:create", args=[self.product.slug]),
            {"rating": 4, "title": "Again", "content": "Duplicate."},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "already reviewed")
        self.assertEqual(Review.objects.filter(product=self.product, user=self.user).count(), 1)

    def test_duplicate_review_integrity_error_returns_form_error(self):
        self.client.force_login(self.user)
        with patch("apps.reviews.views.Review.objects.filter") as review_filter:
            review_filter.return_value.exists.return_value = False
            with patch.object(Review, "save", side_effect=IntegrityError):
                response = self.client.post(
                    reverse("reviews:create", args=[self.product.slug]),
                    {"rating": 4, "title": "Race", "content": "Duplicate race."},
                )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "already reviewed")

    def test_product_detail_only_prefetches_approved_reviews(self):
        approved = Review.objects.create(product=self.product, user=self.user, rating=5, title="Approved", content="Visible.", is_approved=True)
        Review.objects.create(product=self.product, user=self.other_user, rating=1, title="Pending", content="Hidden.", is_approved=False)
        response = self.client.get(reverse("catalog:product_detail", args=[self.product.slug]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(response.context["product"].approved_reviews), [approved])

    def test_guest_cart_merge_never_creates_zero_quantity_items(self):
        source = Cart.objects.create(session_key="guest-source")
        target = Cart.objects.create(user=self.user)
        zero_stock = Product.objects.create(
            category=self.category,
            name="Unavailable",
            slug="unavailable",
            sku="UNAVAILABLE-001",
            description="Out of stock.",
            price=Decimal("10.00"),
            stock_quantity=0,
        )
        CartItem.objects.create(cart=source, product=zero_stock, quantity=1)
        CartItem.objects.create(cart=source, product=self.product, quantity=4)
        merge_carts(target, source)
        self.assertFalse(CartItem.objects.filter(cart=target, product=zero_stock).exists())
        self.assertEqual(CartItem.objects.get(cart=target, product=self.product).quantity, 4)

    def test_guest_cart_merge_caps_duplicates_and_skips_inactive_products(self):
        source = Cart.objects.create(session_key="guest-duplicate")
        target = Cart.objects.create(user=self.user)
        CartItem.objects.create(cart=target, product=self.product, quantity=2)
        CartItem.objects.create(cart=source, product=self.product, quantity=4)
        inactive = Product.objects.create(
            category=self.category,
            name="Inactive",
            slug="inactive",
            sku="INACTIVE-001",
            description="Inactive product.",
            price=Decimal("10.00"),
            stock_quantity=3,
            is_active=False,
        )
        CartItem.objects.create(cart=source, product=inactive, quantity=1)
        merge_carts(target, source)
        self.assertEqual(CartItem.objects.get(cart=target, product=self.product).quantity, 5)
        self.assertFalse(CartItem.objects.filter(cart=target, product=inactive).exists())

    def test_guest_cart_merge_rolls_back_on_failure(self):
        source = Cart.objects.create(session_key="guest-rollback")
        target = Cart.objects.create(user=self.user)
        CartItem.objects.create(cart=source, product=self.product, quantity=1)
        with patch("apps.cart.services.CartItem.save", side_effect=RuntimeError):
            with self.assertRaises(RuntimeError):
                merge_carts(target, source)
        self.assertTrue(CartItem.objects.filter(cart=source, product=self.product).exists())
        self.assertFalse(CartItem.objects.filter(cart=target).exists())
    def test_cart_mutations_and_session_isolation(self):
        cart = Cart.objects.create(user=self.user)
        item = CartItem.objects.create(cart=cart, product=self.product, quantity=2)
        self.client.force_login(self.user)
        self.client.post(reverse("cart:update", args=[item.pk]), {"quantity": 3})
        item.refresh_from_db()
        self.assertEqual(item.quantity, 3)
        self.client.post(reverse("cart:remove", args=[item.pk]))
        self.assertFalse(CartItem.objects.filter(pk=item.pk).exists())
        CartItem.objects.create(cart=cart, product=self.product, quantity=1)
        self.client.post(reverse("cart:clear"))
        self.assertFalse(cart.items.exists())
        guest_client = Client()
        guest_client.get(reverse("cart:detail"))
        guest_session_key = guest_client.session.session_key
        guest_cart = Cart.objects.create(session_key=guest_session_key)
        self.assertIsNone(guest_cart.user)
        self.assertEqual(cart.user, self.user)

    def test_dashboard_requires_staff_and_aggregates(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(reverse("dashboard:index")).status_code, 403)
        staff = User.objects.create_user(username="staff", password="Correct-password-123", is_staff=True)
        self.client.force_login(staff)
        self.assertEqual(self.client.get(reverse("dashboard:index")).status_code, 200)
        self.assertEqual(dashboard_stats()["product_count"], 1)

    def test_dashboard_revenue_excludes_unpaid_orders_consistently(self):
        for number, payment_status in (("LM-UNPAID-001", Order.PaymentStatus.PENDING), ("LM-PAID-002", Order.PaymentStatus.PAID)):
            Order.objects.create(
                order_number=number,
                user=self.user,
                subtotal=Decimal("20.00"),
                shipping_fee=Decimal("0.00"),
                total=Decimal("20.00"),
                shipping_name="Alex",
                shipping_email="alex@example.com",
                shipping_address="123 Main Street",
                status=Order.Status.PROCESSING,
                payment_status=payment_status,
            )
        self.assertEqual(dashboard_stats()["revenue"], Decimal("20.00"))
        self.assertEqual(sales_summary()["revenue"], Decimal("20.00"))

    def test_image_upload_validation_checks_size_and_signature(self):
        valid = SimpleUploadedFile("image.png", b"\x89PNG\r\n\x1a\nvalid", content_type="image/png")
        self.product.main_image = valid
        self.product.full_clean()
        invalid = SimpleUploadedFile("image.png", b"not-an-image", content_type="image/png")
        self.product.main_image = invalid
        with self.assertRaises(ValidationError):
            self.product.full_clean()
