from .models import Wishlist, WishlistItem


def get_wishlist(user):
    wishlist, _ = Wishlist.objects.get_or_create(user=user)
    return wishlist


def add_product(user, product):
    if not product.is_active:
        raise ValueError("This product is unavailable.")
    wishlist = get_wishlist(user)
    item, _ = WishlistItem.objects.get_or_create(wishlist=wishlist, product=product)
    return item
