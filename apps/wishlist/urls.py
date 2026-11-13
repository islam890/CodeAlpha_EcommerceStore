from django.urls import path

from .views import WishlistPageView, add_to_wishlist, remove_from_wishlist

app_name = "wishlist"

urlpatterns = [
    path("", WishlistPageView.as_view(), name="detail"),
    path("add/<slug:slug>/", add_to_wishlist, name="add"),
    path("remove/<int:item_id>/", remove_from_wishlist, name="remove"),
]
