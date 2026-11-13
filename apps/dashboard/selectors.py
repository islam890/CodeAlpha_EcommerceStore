from django.contrib.auth.models import User
from django.db.models import Count, Sum

from apps.catalog.models import Product
from apps.orders.models import Order


def dashboard_stats():
    revenue = Order.objects.filter(
        status__in=(Order.Status.PROCESSING, Order.Status.SHIPPED, Order.Status.DELIVERED),
        payment_status=Order.PaymentStatus.PAID,
    ).aggregate(total=Sum("total"))["total"] or 0
    return {
        "product_count": Product.objects.count(),
        "customer_count": User.objects.filter(is_staff=False).count(),
        "order_count": Order.objects.count(),
        "revenue": revenue,
        "recent_orders": Order.objects.select_related("user").prefetch_related("items")[:5],
        "low_stock_products": Product.objects.filter(is_active=True, stock_quantity__lte=5).order_by("stock_quantity")[:10],
    }


def sales_summary():
    return Order.objects.filter(
        status__in=(Order.Status.PROCESSING, Order.Status.SHIPPED, Order.Status.DELIVERED),
        payment_status=Order.PaymentStatus.PAID,
    ).aggregate(
        revenue=Sum("total"),
        orders=Count("id"),
    )
