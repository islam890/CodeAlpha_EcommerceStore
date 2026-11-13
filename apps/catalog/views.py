from django.db.models import Q
from django.db.models import Prefetch
from django.views.generic import DetailView, ListView, TemplateView

from .models import Category, Product
from apps.reviews.models import Review


class HomePageView(TemplateView):
    template_name = "home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        featured = Product.objects.filter(
            is_active=True, is_featured=True
        ).select_related("category").prefetch_related("images")[:4]
        context["products"] = featured if featured.exists() else Product.objects.filter(
            is_active=True
        ).select_related("category").prefetch_related("images")[:4]
        context["categories"] = Category.objects.filter(is_active=True)[:4]
        return context


class ProductListPageView(ListView):
    template_name = "catalog/product_list.html"
    context_object_name = "products"
    paginate_by = 12

    def get_queryset(self):
        queryset = Product.objects.filter(is_active=True).select_related("category")
        query = self.request.GET.get("q", "").strip()
        category = self.request.GET.get("category", "").strip()
        if query:
            queryset = queryset.filter(Q(name__icontains=query) | Q(description__icontains=query) | Q(sku__icontains=query))
        if category:
            queryset = queryset.filter(category__slug=category)
        ordering = self.request.GET.get("sort")
        if ordering in {"price", "-price", "name", "-created_at"}:
            queryset = queryset.order_by(ordering)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["categories"] = Category.objects.filter(is_active=True)
        return context


class ProductDetailPageView(DetailView):
    template_name = "catalog/product_detail.html"
    context_object_name = "product"
    slug_url_kwarg = "slug"

    def get_queryset(self):
        approved_reviews = Review.objects.filter(is_approved=True).select_related("user")
        return Product.objects.filter(is_active=True).select_related("category").prefetch_related(
            "images",
            Prefetch("reviews", queryset=approved_reviews, to_attr="approved_reviews"),
        )


class CategoryListPageView(ListView):
    template_name = "catalog/category_list.html"
    context_object_name = "categories"

    def get_queryset(self):
        return Category.objects.filter(is_active=True)


class SearchResultsPageView(ProductListPageView):
    template_name = "catalog/search_results.html"
