from django.contrib import messages
from django.views.decorators.http import require_POST
from django.shortcuts import get_object_or_404, redirect
from django.views.generic import TemplateView

from apps.catalog.models import Product

from .forms import CartItemForm
from .models import Cart, CartItem
from .services import add_item, get_cart, update_item


class CartPageView(TemplateView):
    template_name = "cart/cart_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        cart = get_cart(user=self.request.user, session_key=self.request.session.session_key)
        context["cart"] = cart
        context["cart_items"] = cart.items.select_related("product") if cart else []
        return context


def _session_cart(request):
    if not request.session.session_key:
        request.session.create()
    cart, _ = Cart.objects.get_or_create(session_key=request.session.session_key)
    return cart


@require_POST
def add_to_cart(request, slug):
    product = get_object_or_404(Product, slug=slug, is_active=True)
    cart = get_cart(user=request.user, session_key=request.session.session_key) if request.user.is_authenticated else _session_cart(request)
    form = CartItemForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            add_item(cart, product, form.cleaned_data["quantity"])
        except ValueError as exc:
            messages.error(request, str(exc))
        else:
            messages.success(request, "Product added to your bag.")
    return redirect("cart:detail")


@require_POST
def update_cart_item(request, item_id):
    item = get_object_or_404(CartItem, pk=item_id)
    cart = get_cart(user=request.user, session_key=request.session.session_key)
    if cart and item.cart_id == cart.id:
        form = CartItemForm(request.POST)
        if form.is_valid():
            try:
                update_item(item, form.cleaned_data["quantity"])
            except ValueError as exc:
                messages.error(request, str(exc))
    return redirect("cart:detail")


@require_POST
def remove_cart_item(request, item_id):
    item = get_object_or_404(CartItem, pk=item_id)
    cart = get_cart(user=request.user, session_key=request.session.session_key)
    if cart and item.cart_id == cart.id:
        item.delete()
    return redirect("cart:detail")


@require_POST
def clear_cart(request):
    cart = get_cart(user=request.user, session_key=request.session.session_key)
    if cart:
        cart.items.all().delete()
    return redirect("cart:detail")
