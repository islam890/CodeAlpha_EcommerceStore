from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views.decorators.http import require_POST
from django.views.generic import DetailView, FormView, ListView, TemplateView

from apps.cart.models import Cart

from .forms import CheckoutForm
from .models import Order
from .services import cancel_order, create_order, shipping_fee_for


class CheckoutPageView(LoginRequiredMixin, FormView):
    template_name = "orders/checkout.html"
    form_class = CheckoutForm
    success_url = reverse_lazy("orders:confirmation")

    def get_initial(self):
        profile = getattr(self.request.user, "profile", None)
        return {
            "shipping_name": self.request.user.get_full_name(),
            "shipping_email": self.request.user.email,
            "shipping_phone": profile.phone if profile else "",
            "shipping_address": profile.address_line_1 if profile else "",
            "payment_method": Order.PaymentMethod.COD,
        }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["cart"] = Cart.objects.filter(user=self.request.user).first()
        context["has_cart_items"] = bool(context["cart"] and context["cart"].items.exists())
        if context["cart"]:
            context["cart_items"] = context["cart"].items.select_related("product")
            subtotal = sum((item.line_total for item in context["cart_items"]), Decimal("0.00"))
            context["shipping_fee"] = shipping_fee_for(subtotal)
            context["checkout_total"] = subtotal + context["shipping_fee"]
        return context

    def form_valid(self, form):
        cart = Cart.objects.filter(user=self.request.user).first()
        try:
            self.order = create_order(user=self.request.user, cart=cart, checkout_data=form.cleaned_data)
        except ValueError as exc:
            form.add_error(None, str(exc))
            return self.form_invalid(form)
        self.request.session["last_order_number"] = self.order.order_number
        return super().form_valid(form)


class OrderConfirmationPageView(LoginRequiredMixin, TemplateView):
    template_name = "orders/order_confirmation.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        number = self.request.session.get("last_order_number")
        context["order"] = Order.objects.filter(user=self.request.user, order_number=number).first()
        return context


class OrderHistoryPageView(LoginRequiredMixin, ListView):
    template_name = "orders/order_history.html"
    context_object_name = "orders"
    paginate_by = 25

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user).prefetch_related("items")


class OrderDetailPageView(LoginRequiredMixin, DetailView):
    template_name = "orders/order_detail.html"
    context_object_name = "order"
    slug_url_kwarg = "order_number"
    slug_field = "order_number"

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user).prefetch_related("items__product")


@login_required
@require_POST
def cancel_order_view(request, order_number):
    order = get_object_or_404(Order, order_number=order_number, user=request.user)
    try:
        cancel_order(order)
    except ValueError as exc:
        messages.error(request, str(exc))
    else:
        messages.success(request, "Your order has been cancelled.")
    return redirect("orders:detail", order_number=order.order_number)
