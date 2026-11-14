from django import forms
from django.contrib import admin

from .services import transition_order_state
from .models import Order, OrderItem


class OrderAdminForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = "__all__"

    def clean(self):
        cleaned_data = super().clean()
        if not self.instance.pk:
            return cleaned_data

        current_status = self.instance.status
        new_status = cleaned_data.get("status", current_status)
        if not Order.is_valid_status_transition(current_status, new_status):
            self.add_error("status", "This order status transition is not allowed.")

        current_payment_status = self.instance.payment_status
        new_payment_status = cleaned_data.get("payment_status", current_payment_status)
        if not Order.is_valid_payment_transition(current_payment_status, new_payment_status):
            self.add_error("payment_status", "This payment status transition is not allowed.")
        return cleaned_data


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ("product_name", "sku", "unit_price", "quantity", "line_total")


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    form = OrderAdminForm
    list_display = ("order_number", "user", "status", "payment_status", "total", "created_at")
    list_filter = ("status", "payment_method", "payment_status")
    search_fields = ("order_number", "user__username", "shipping_email")
    readonly_fields = ("order_number", "user", "subtotal", "shipping_fee", "total", "created_at", "updated_at")
    inlines = (OrderItemInline,)

    def save_model(self, request, obj, form, change):
        if change:
            transition_order_state(
                obj,
                status=obj.status,
                payment_status=obj.payment_status,
            )
            return
        super().save_model(request, obj, form, change)
