from django.urls import path

from .views import ReviewEditView, ReviewPageView, delete_review

app_name = "reviews"

urlpatterns = [
    path("product/<slug:slug>/", ReviewPageView.as_view(), name="create"),
    path("<int:pk>/edit/", ReviewEditView.as_view(), name="edit"),
    path("<int:pk>/delete/", delete_review, name="delete"),
]
