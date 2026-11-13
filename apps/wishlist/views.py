from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.decorators.http import require_POST
from django.shortcuts import get_object_or_404, redirect
from django.views.generic import TemplateView

from apps.catalog.models import Product

from .models import WishlistItem
from .services import add_product, get_wishlist


class WishlistPageView(LoginRequiredMixin, TemplateView):
    template_name = "wishlist/detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["wishlist"] = get_wishlist(self.request.user)
        context["wishlist_items"] = context["wishlist"].items.select_related("product")
        return context


@login_required
@require_POST
def add_to_wishlist(request, slug):
    product = get_object_or_404(Product, slug=slug)
    try:
        add_product(request.user, product)
    except ValueError as exc:
        messages.error(request, str(exc))
    return redirect("wishlist:detail")


@login_required
@require_POST
def remove_from_wishlist(request, item_id):
    WishlistItem.objects.filter(pk=item_id, wishlist__user=request.user).delete()
    return redirect("wishlist:detail")
