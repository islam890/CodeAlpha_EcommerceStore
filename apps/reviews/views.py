from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, UpdateView

from apps.catalog.models import Product

from .forms import ReviewForm
from .models import Review


class ReviewPageView(LoginRequiredMixin, CreateView):
    template_name = "reviews/review_form.html"
    form_class = ReviewForm

    def dispatch(self, request, *args, **kwargs):
        self.product = get_object_or_404(Product, slug=kwargs["slug"], is_active=True)
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.product = self.product
        form.instance.user = self.request.user
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["product"] = self.product
        return context

    def get_success_url(self):
        return reverse("catalog:product_detail", kwargs={"slug": self.product.slug}) + "#reviews"


class ReviewEditView(LoginRequiredMixin, UpdateView):
    template_name = "reviews/review_form.html"
    form_class = ReviewForm
    context_object_name = "review"

    def get_queryset(self):
        return Review.objects.filter(user=self.request.user).select_related("product")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["product"] = self.object.product
        return context

    def form_valid(self, form):
        form.instance.is_approved = False
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("catalog:product_detail", kwargs={"slug": self.object.product.slug}) + "#reviews"


@login_required
@require_POST
def delete_review(request, pk):
    Review.objects.filter(pk=pk, user=request.user).delete()
    return redirect("accounts:profile")
