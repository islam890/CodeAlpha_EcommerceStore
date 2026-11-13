from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth import views as auth_views
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.views.generic import CreateView, UpdateView

from .forms import EmailPasswordResetForm, ProfileForm, RegistrationForm
from .models import Profile
from apps.reviews.models import Review


class LoginPageView(auth_views.LoginView):
    template_name = "accounts/login.html"
    redirect_authenticated_user = True


class RegisterPageView(CreateView):
    form_class = RegistrationForm
    template_name = "accounts/register.html"
    success_url = reverse_lazy("accounts:profile")

    def form_valid(self, form):
        response = super().form_valid(form)
        login(self.request, self.object)
        return response


class ProfilePageView(LoginRequiredMixin, auth_views.TemplateView):
    template_name = "accounts/profile.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["reviews"] = Review.objects.filter(user=self.request.user).select_related("product")
        context["order_count"] = self.request.user.orders.count()
        return context


class ProfileEditPageView(LoginRequiredMixin, UpdateView):
    model = Profile
    form_class = ProfileForm
    template_name = "accounts/profile_edit.html"
    success_url = reverse_lazy("accounts:profile")

    def get_object(self, queryset=None):
        profile, _ = Profile.objects.get_or_create(user=self.request.user)
        return profile


class PasswordResetPageView(auth_views.PasswordResetView):
    form_class = EmailPasswordResetForm
    template_name = "accounts/password_reset.html"
    email_template_name = "registration/password_reset_email.txt"
    success_url = reverse_lazy("password_reset_done")


class PasswordChangePageView(LoginRequiredMixin, auth_views.PasswordChangeView):
    template_name = "accounts/password_change.html"
    success_url = reverse_lazy("accounts:profile")
