from django import forms

from .models import Order


class CheckoutForm(forms.Form):
    shipping_name = forms.CharField(max_length=200)
    shipping_email = forms.EmailField()
    shipping_phone = forms.CharField(max_length=30, required=False)
    shipping_address = forms.CharField(widget=forms.Textarea)
    payment_method = forms.ChoiceField(choices=Order.PaymentMethod.choices)


class OrderStatusForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ("status", "payment_status")
