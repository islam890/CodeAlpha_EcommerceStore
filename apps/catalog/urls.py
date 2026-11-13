from django.urls import path

from .views import (
    CategoryListPageView,
    ProductDetailPageView,
    ProductListPageView,
    SearchResultsPageView,
)

app_name = "catalog"

urlpatterns = [
    path("", ProductListPageView.as_view(), name="product_list"),
    path("products/", ProductListPageView.as_view(), name="products"),
    path("products/<slug:slug>/", ProductDetailPageView.as_view(), name="product_detail"),
    path("categories/", CategoryListPageView.as_view(), name="categories"),
    path("search/", SearchResultsPageView.as_view(), name="search"),
]
