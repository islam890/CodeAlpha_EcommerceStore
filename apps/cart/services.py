from django.db import transaction

from apps.catalog.models import Product

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
    """Merge a guest cart into an owned cart.

    The cart and item locks protect merges on databases that support row-level
    locking. SQLite remains subject to its database-wide write-lock behavior.
    """
    if target.pk == source.pk:
        return
    try:
        locked_target = Cart.objects.select_for_update().get(pk=target.pk)
        locked_source = Cart.objects.select_for_update().get(pk=source.pk)
    except Cart.DoesNotExist:
        return

    for item in locked_source.items.select_for_update():
        product = Product.objects.select_for_update().get(pk=item.product_id)
        available_stock = product.stock_quantity
        if available_stock < 1 or not product.is_active:
            item.delete()
            continue
        existing = (
            locked_target.items.select_for_update()
            .filter(product_id=product.pk)
            .first()
        )
        if existing:
            existing.quantity = min(existing.quantity + item.quantity, available_stock)
            existing.save(update_fields=("quantity", "updated_at"))
        else:
            item.quantity = min(item.quantity, available_stock)
            item.pk = None
            item.cart = locked_target
            item.save()
    locked_source.delete()


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
