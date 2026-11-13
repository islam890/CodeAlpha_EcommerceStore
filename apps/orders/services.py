from decimal import Decimal
from uuid import uuid4

from django.db import transaction

from apps.cart.models import Cart
from apps.catalog.models import Product

from .models import Order, OrderItem


def shipping_fee_for(subtotal):
    return Decimal("0.00") if subtotal >= Decimal("100.00") else Decimal("8.00")


@transaction.atomic
def create_order(*, user, cart, checkout_data):
    """Create one order and consume its cart.

    Locking prevents sequential duplicate submissions from reusing a cart.
    SQLite does not provide production-grade row-level locking; use PostgreSQL
    (or another transactional database with row locks) for concurrent checkout.
    """
    if cart is None or cart.user_id != user.id:
        raise ValueError("Your cart is unavailable.")
    locked_cart = Cart.objects.select_for_update().filter(pk=cart.pk, user=user).first()
    if locked_cart is None:
        raise ValueError("Your cart is unavailable.")
    items = list(locked_cart.items.select_related("product").select_for_update())
    if not items:
        raise ValueError("Your cart is empty.")
    subtotal = Decimal("0.00")
    for item in items:
        product = item.product
        if not product.is_in_stock or item.quantity > product.stock_quantity:
            raise ValueError(f"{product.name} does not have enough stock.")
        subtotal += product.price * item.quantity
    shipping_fee = shipping_fee_for(subtotal)
    order = Order.objects.create(
        order_number=f"LM-{uuid4().hex[:12].upper()}",
        user=user,
        subtotal=subtotal,
        shipping_fee=shipping_fee,
        total=subtotal + shipping_fee,
        shipping_name=checkout_data["shipping_name"],
        shipping_email=checkout_data["shipping_email"],
        shipping_phone=checkout_data.get("shipping_phone", ""),
        shipping_address=checkout_data["shipping_address"],
        payment_method=checkout_data["payment_method"],
    )
    for item in items:
        product = item.product
        line_total = product.price * item.quantity
        OrderItem.objects.create(
            order=order,
            product=product,
            product_name=product.name,
            sku=product.sku,
            unit_price=product.price,
            quantity=item.quantity,
            line_total=line_total,
        )
        product.stock_quantity -= item.quantity
        product.save(update_fields=("stock_quantity", "updated_at"))
    locked_cart.delete()
    return order


@transaction.atomic
def cancel_order(order):
    locked_order = (
        Order.objects.select_for_update()
        .prefetch_related("items__product")
        .get(pk=order.pk)
    )
    if locked_order.status not in {Order.Status.PENDING, Order.Status.PROCESSING}:
        raise ValueError("This order can no longer be cancelled.")
    if locked_order.payment_status == Order.PaymentStatus.PAID:
        raise ValueError("Paid orders require a refund workflow before cancellation.")
    for item in locked_order.items.all():
        if item.product_id:
            product = Product.objects.select_for_update().get(pk=item.product_id)
            product.stock_quantity += item.quantity
            product.save(update_fields=("stock_quantity", "updated_at"))
    locked_order.status = Order.Status.CANCELLED
    locked_order.save(update_fields=("status", "updated_at"))
    order.status = locked_order.status
    order.updated_at = locked_order.updated_at
    return locked_order
