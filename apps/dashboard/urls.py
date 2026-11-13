from django.urls import path

from .views import (
    DashboardPageView,
    OrderManagementPageView,
    ProductManagementPageView,
    SalesStatisticsPageView,
)

app_name = "dashboard"

urlpatterns = [
    path("", DashboardPageView.as_view(), name="index"),
    path("products/", ProductManagementPageView.as_view(), name="products"),
    path("orders/", OrderManagementPageView.as_view(), name="orders"),
    path("sales/", SalesStatisticsPageView.as_view(), name="sales"),
]
