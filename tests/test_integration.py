from decimal import Decimal

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from apps.catalog.models import Category, Product
from apps.orders.models import Order
from apps.reviews.models import Review
from apps.wishlist.models import WishlistItem


class StorefrontIntegrationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="customer",
            password="Correct-password-123",
            email="customer@example.com",
            first_name="Casey",
        )
        self.other_user = User.objects.create_user(
            username="other",
            password="Correct-password-123",
        )
        self.category = Category.objects.create(
            name="Home",
            slug="home",
            description="Objects for everyday rituals.",
        )
        self.product = Product.objects.create(
            category=self.category,
            name="Daily Mug",
            slug="daily-mug",
            sku="MUG-INT-001",
            description="A considered ceramic mug.",
            price=Decimal("25.00"),
            stock_quantity=4,
            is_featured=True,
        )

    def test_home_catalog_search_category_and_detail_render_real_data(self):
        response = self.client.get(reverse("home"))
        self.assertContains(response, self.product.name)
        self.assertContains(response, self.category.name)

        response = self.client.get(reverse("catalog:products"), {"q": "Daily"})
        self.assertContains(response, self.product.name)
        response = self.client.get(reverse("catalog:products"), {"category": self.category.slug})
        self.assertContains(response, self.product.name)
        response = self.client.get(reverse("catalog:search"), {"q": "missing"})
        self.assertContains(response, "No matching products")
        response = self.client.get(reverse("catalog:product_detail", args=[self.product.slug]))
        self.assertContains(response, self.product.description)
        self.assertContains(response, "Add to bag")
        self.assertEqual(
            self.client.get(reverse("catalog:product_detail", args=["does-not-exist"])).status_code,
            404,
        )

    def test_registration_login_and_profile_render_user_data(self):
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
        self.assertRedirects(response, reverse("accounts:profile"))
        response = self.client.get(reverse("accounts:profile"))
        self.assertContains(response, "new@example.com")

    def test_cart_wishlist_checkout_and_order_history_flow(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("cart:add", args=[self.product.slug]),
            {"quantity": 2},
        )
        self.assertRedirects(response, reverse("cart:detail"))
        self.assertContains(self.client.get(reverse("cart:detail")), "Daily Mug")

        response = self.client.post(
            reverse("wishlist:add", args=[self.product.slug]),
        )
        self.assertRedirects(response, reverse("wishlist:detail"))
        self.assertEqual(WishlistItem.objects.filter(wishlist__user=self.user).count(), 1)

        response = self.client.post(
            reverse("orders:checkout"),
            {
                "shipping_name": "Casey Customer",
                "shipping_email": "customer@example.com",
                "shipping_phone": "",
                "shipping_address": "123 Main Street",
                "payment_method": Order.PaymentMethod.COD,
            },
        )
        self.assertRedirects(response, reverse("orders:confirmation"))
        order = Order.objects.get(user=self.user)
        self.assertContains(self.client.get(reverse("orders:history")), order.order_number)
        self.assertContains(
            self.client.get(reverse("orders:detail", args=[order.order_number])),
            order.items.get().product_name,
        )

    def test_reviews_show_approved_only_and_accept_submission(self):
        approved = Review.objects.create(
            product=self.product,
            user=self.other_user,
            rating=5,
            title="Excellent",
            content="Approved review.",
            is_approved=True,
        )
        Review.objects.create(
            product=self.product,
            user=User.objects.create_user(username="pending"),
            rating=3,
            title="Pending",
            content="Pending review.",
            is_approved=False,
        )
        response = self.client.get(reverse("catalog:product_detail", args=[self.product.slug]))
        self.assertContains(response, approved.content)
        self.assertNotContains(response, "Pending review.")
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("reviews:create", args=[self.product.slug]),
            {"rating": 4, "title": "New", "content": "New review."},
        )
        self.assertRedirects(
            response,
            reverse("catalog:product_detail", args=[self.product.slug]) + "#reviews",
        )

    def test_inactive_wishlist_addition_is_safe(self):
        self.product.is_active = False
        self.product.save(update_fields=("is_active",))
        self.client.force_login(self.user)
        response = self.client.post(reverse("wishlist:add", args=[self.product.slug]))
        self.assertRedirects(response, reverse("wishlist:detail"))
        self.assertFalse(WishlistItem.objects.filter(wishlist__user=self.user).exists())

    def test_dashboard_is_staff_only_and_empty_states_render(self):
        self.assertEqual(self.client.get(reverse("dashboard:index")).status_code, 302)
        self.assertContains(self.client.get(reverse("cart:detail")), "Your bag is empty")
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(reverse("dashboard:index")).status_code, 403)
        staff = User.objects.create_user(
            username="staff",
            password="Correct-password-123",
            is_staff=True,
        )
        self.client.force_login(staff)
        self.assertContains(self.client.get(reverse("dashboard:index")), "Revenue")
        self.assertContains(self.client.get(reverse("dashboard:products")), self.product.name)
        self.assertContains(self.client.get(reverse("dashboard:orders")), "No orders yet")

    def test_state_changing_requests_require_csrf(self):
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.user)
        response = csrf_client.post(
            reverse("cart:add", args=[self.product.slug]),
            {"quantity": 1},
        )
        self.assertEqual(response.status_code, 403)

    def test_account_and_staff_templates_resolve_all_named_routes(self):
        self.assertEqual(self.client.get(reverse("accounts:login")).status_code, 200)
        self.assertEqual(self.client.get(reverse("accounts:register")).status_code, 200)
        self.assertEqual(self.client.get(reverse("accounts:password_reset")).status_code, 200)
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(reverse("accounts:profile_edit")).status_code, 200)
        self.assertEqual(self.client.get(reverse("accounts:password_change")).status_code, 200)
        self.client.post(reverse("accounts:logout"))
        staff = User.objects.create_user(
            username="staff-routes",
            password="Correct-password-123",
            is_staff=True,
        )
        self.client.force_login(staff)
        self.assertEqual(self.client.get(reverse("dashboard:sales")).status_code, 200)
