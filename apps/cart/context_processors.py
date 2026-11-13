from django.db.models import Sum

from .models import Cart


def cart_summary(request):
    cart = None
    if request.user.is_authenticated:
        cart = Cart.objects.filter(user=request.user).first()
    elif request.session.session_key:
        cart = Cart.objects.filter(session_key=request.session.session_key).first()
    return {
        "current_cart": cart,
        "cart_item_count": (
            cart.items.aggregate(total=Sum("quantity"))["total"] or 0
            if cart
            else 0
        ),
    }
