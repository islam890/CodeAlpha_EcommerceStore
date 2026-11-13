from django.contrib.auth.mixins import UserPassesTestMixin
from django.views.generic import TemplateView

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


class ProductManagementPageView(StaffRequiredMixin, TemplateView):
    template_name = "dashboard/product_management.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["products"] = Product.objects.select_related("category").order_by("name")
        return context


class OrderManagementPageView(StaffRequiredMixin, TemplateView):
    template_name = "dashboard/order_management.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["orders"] = Order.objects.select_related("user").prefetch_related("items")
        return context


class SalesStatisticsPageView(StaffRequiredMixin, TemplateView):
    template_name = "dashboard/sales_statistics.html"

    def get_context_data(self, **kwargs):
        return {**super().get_context_data(**kwargs), "summary": sales_summary()}
