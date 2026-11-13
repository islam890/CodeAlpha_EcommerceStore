from django.contrib.auth import views as auth_views
from django.urls import path

from .views import (
    LoginPageView,
    PasswordChangePageView,
    PasswordResetPageView,
    ProfileEditPageView,
    ProfilePageView,
    RegisterPageView,
)

app_name = "accounts"

urlpatterns = [
    path("login/", LoginPageView.as_view(), name="login"),
    path("register/", RegisterPageView.as_view(), name="register"),
    path("password-reset/", PasswordResetPageView.as_view(), name="password_reset"),
    path("password-change/", PasswordChangePageView.as_view(), name="password_change"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("profile/", ProfilePageView.as_view(), name="profile"),
    path("profile/edit/", ProfileEditPageView.as_view(), name="profile_edit"),
]
