from decimal import Decimal
from uuid import uuid4

from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import transaction

from apps.cart.models import Cart
from apps.catalog.models import Product

from .models import Order, OrderItem


def shipping_fee_for(subtotal):
    return Decimal("0.00") if subtotal >= Decimal("100.00") else Decimal("8.00")


def _validate_checkout_data(checkout_data):
    if not hasattr(checkout_data, "get"):
        raise ValueError("Checkout data is invalid.")
    shipping_name = checkout_data.get("shipping_name")
    shipping_email = checkout_data.get("shipping_email")
    shipping_address = checkout_data.get("shipping_address")
    payment_method = checkout_data.get("payment_method")
    if not all(
        isinstance(value, str) and value.strip()
        for value in (shipping_name, shipping_email, shipping_address, payment_method)
    ):
        missing_field = next(
            field
            for field, value in (
                ("shipping_name", shipping_name),
                ("shipping_email", shipping_email),
                ("shipping_address", shipping_address),
                ("payment_method", payment_method),
            )
            if not isinstance(value, str) or not value.strip()
        )
        raise ValueError(f"{missing_field.replace('_', ' ').capitalize()} is required.")
    if payment_method not in Order.PaymentMethod.values:
        raise ValueError("This payment method is not supported.")
    if len(shipping_name) > 200:
        raise ValueError("Shipping name is too long.")
    shipping_phone = checkout_data.get("shipping_phone", "") or ""
    if not isinstance(shipping_phone, str) or len(shipping_phone) > 30:
        raise ValueError("Shipping phone is too long.")
    try:
        validate_email(shipping_email)
    except ValidationError as exc:
        raise ValueError("Enter a valid shipping email.") from exc


def _transition_locked_order_state(locked_order, *, status=None, payment_status=None):
    new_status = locked_order.status if status is None else status
    new_payment_status = (
        locked_order.payment_status if payment_status is None else payment_status
    )
    if not Order.is_valid_status_transition(locked_order.status, new_status):
        raise ValueError("This order status transition is not allowed.")
    if not Order.is_valid_payment_transition(locked_order.payment_status, new_payment_status):
        raise ValueError("This payment status transition is not allowed.")
    if new_status == Order.Status.CANCELLED and new_payment_status == Order.PaymentStatus.PAID:
        raise ValueError("Paid orders require a refund workflow before cancellation.")

    update_fields = []
    if new_status != locked_order.status:
        locked_order.status = new_status
        update_fields.append("status")
    if new_payment_status != locked_order.payment_status:
        locked_order.payment_status = new_payment_status
        update_fields.append("payment_status")
    if update_fields:
        update_fields.append("updated_at")
        locked_order.save(update_fields=update_fields)
    return locked_order


@transaction.atomic
def transition_order_state(order, *, status=None, payment_status=None):
    locked_order = Order.objects.select_for_update().get(pk=order.pk)
    return _transition_locked_order_state(
        locked_order,
        status=status,
        payment_status=payment_status,
    )


def transition_order_status(order, new_status):
    return transition_order_state(order, status=new_status)


def transition_payment_status(order, new_payment_status):
    return transition_order_state(order, payment_status=new_payment_status)


@transaction.atomic
def create_order(*, user, cart, checkout_data):
    """Create one order and consume its cart.

    Locking prevents sequential duplicate submissions from reusing a cart.
    SQLite does not provide production-grade row-level locking; use PostgreSQL
    (or another transactional database with row locks) for concurrent checkout.
    """
    _validate_checkout_data(checkout_data)
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
        if (
            not isinstance(item.quantity, int)
            or isinstance(item.quantity, bool)
            or item.quantity < 1
        ):
            raise ValueError("Cart quantities must be positive whole numbers.")
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
        shipping_phone=checkout_data.get("shipping_phone", "") or "",
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
    if (
        locked_order.status == Order.Status.CANCELLED
        or not Order.is_valid_status_transition(locked_order.status, Order.Status.CANCELLED)
    ):
        raise ValueError("This order can no longer be cancelled.")
    if locked_order.payment_status == Order.PaymentStatus.PAID:
        raise ValueError("Paid orders require a refund workflow before cancellation.")
    for item in locked_order.items.all():
        if item.product_id:
            product = Product.objects.select_for_update().get(pk=item.product_id)
            product.stock_quantity += item.quantity
            product.save(update_fields=("stock_quantity", "updated_at"))
    _transition_locked_order_state(locked_order, status=Order.Status.CANCELLED)
    order.status = locked_order.status
    order.updated_at = locked_order.updated_at
    return locked_order
