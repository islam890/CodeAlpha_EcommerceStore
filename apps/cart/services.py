from django.db import transaction

from .models import Cart, CartItem


def get_cart(*, user=None, session_key=None):
    if user is not None and user.is_authenticated:
        cart, _ = Cart.objects.get_or_create(user=user)
        if session_key:
            guest = Cart.objects.filter(session_key=session_key).first()
            if guest and guest.pk != cart.pk:
                merge_carts(cart, guest)
        return cart
    if not session_key:
        return None
    return Cart.objects.filter(session_key=session_key).first()


@transaction.atomic
def merge_carts(target, source):
    for item in source.items.select_related("product"):
        available_stock = item.product.stock_quantity
        if available_stock < 1 or not item.product.is_active:
            item.delete()
            continue
        existing = target.items.filter(product=item.product).first()
        if existing:
            existing.quantity = min(existing.quantity + item.quantity, available_stock)
            existing.save(update_fields=("quantity", "updated_at"))
        else:
            item.quantity = min(item.quantity, available_stock)
            item.pk = None
            item.cart = target
            item.save()
    source.delete()


@transaction.atomic
def add_item(cart, product, quantity):
    if not product.is_in_stock:
        raise ValueError("This product is currently unavailable.")
    if quantity < 1:
        raise ValueError("Quantity must be at least one.")
    item, created = CartItem.objects.get_or_create(cart=cart, product=product, defaults={"quantity": quantity})
    if not created:
        quantity += item.quantity
        item.quantity = quantity
    if item.quantity > product.stock_quantity:
        raise ValueError("Requested quantity exceeds available stock.")
    item.save()
    return item


@transaction.atomic
def update_item(item, quantity):
    if quantity < 1:
        item.delete()
        return
    if not item.product.is_in_stock or quantity > item.product.stock_quantity:
        raise ValueError("Requested quantity exceeds available stock.")
    item.quantity = quantity
    item.save(update_fields=("quantity", "updated_at"))
