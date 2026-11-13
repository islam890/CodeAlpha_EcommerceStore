from django.urls import path

from .views import CartPageView, add_to_cart, clear_cart, remove_cart_item, update_cart_item

app_name = "cart"

urlpatterns = [
    path("", CartPageView.as_view(), name="detail"),
    path("add/<slug:slug>/", add_to_cart, name="add"),
    path("update/<int:item_id>/", update_cart_item, name="update"),
    path("remove/<int:item_id>/", remove_cart_item, name="remove"),
    path("clear/", clear_cart, name="clear"),
]
