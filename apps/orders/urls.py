from django.urls import path

from .views import (
    cancel_order_view,
    CheckoutPageView,
    OrderConfirmationPageView,
    OrderDetailPageView,
    OrderHistoryPageView,
)

app_name = "orders"

urlpatterns = [
    path("checkout/", CheckoutPageView.as_view(), name="checkout"),
    path("confirmation/", OrderConfirmationPageView.as_view(), name="confirmation"),
    path("history/", OrderHistoryPageView.as_view(), name="history"),
    path("<str:order_number>/", OrderDetailPageView.as_view(), name="detail"),
    path("<str:order_number>/cancel/", cancel_order_view, name="cancel"),
]
