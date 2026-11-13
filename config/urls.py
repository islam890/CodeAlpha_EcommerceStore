"""Root URL configuration."""

from django.contrib import admin
from django.urls import include, path

from apps.catalog.views import HomePageView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", HomePageView.as_view(), name="home"),
    path("accounts/", include("apps.accounts.urls")),
    path("accounts/", include("django.contrib.auth.urls")),
    path("catalog/", include("apps.catalog.urls")),
    path("cart/", include("apps.cart.urls")),
    path("orders/", include("apps.orders.urls")),
    path("reviews/", include("apps.reviews.urls")),
    path("wishlist/", include("apps.wishlist.urls")),
    path("dashboard/", include("apps.dashboard.urls")),
]
