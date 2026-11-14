from django.contrib.auth.mixins import UserPassesTestMixin
from django.views.generic import ListView, TemplateView

from apps.catalog.models import Product
from apps.orders.models import Order

from .selectors import dashboard_stats, sales_summary


class StaffRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.is_staff


class DashboardPageView(StaffRequiredMixin, TemplateView):
    template_name = "dashboard/index.html"

    def get_context_data(self, **kwargs):
        return {**super().get_context_data(**kwargs), **dashboard_stats()}


class ProductManagementPageView(StaffRequiredMixin, ListView):
    template_name = "dashboard/product_management.html"
    context_object_name = "products"
    paginate_by = 25

    def get_queryset(self):
        return Product.objects.select_related("category").order_by("name", "pk")


class OrderManagementPageView(StaffRequiredMixin, ListView):
    template_name = "dashboard/order_management.html"
    context_object_name = "orders"
    paginate_by = 25

    def get_queryset(self):
        return (
            Order.objects.select_related("user")
            .prefetch_related("items")
            .order_by("-created_at", "-pk")
        )


class SalesStatisticsPageView(StaffRequiredMixin, TemplateView):
    template_name = "dashboard/sales_statistics.html"

    def get_context_data(self, **kwargs):
        return {**super().get_context_data(**kwargs), "summary": sales_summary()}
