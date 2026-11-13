from django import forms

from .models import Category, Product, ProductImage


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ("name", "slug", "description", "image", "is_active")


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = (
            "category",
            "name",
            "slug",
            "sku",
            "description",
            "price",
            "stock_quantity",
            "main_image",
            "is_active",
            "is_featured",
        )


class ProductImageForm(forms.ModelForm):
    class Meta:
        model = ProductImage
        fields = ("image", "alt_text", "display_order")
