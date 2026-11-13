from django.contrib.auth.models import User
from django.core.validators import RegexValidator
from django.db import models

from apps.catalog.validators import validate_image_upload


phone_validator = RegexValidator(
    regex=r"^[0-9+()\- .]{7,30}$",
    message="Enter a valid phone number.",
)


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    phone = models.CharField(max_length=30, blank=True, validators=[phone_validator])
    address_line_1 = models.CharField(max_length=255, blank=True)
    address_line_2 = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, blank=True)
    profile_image = models.FileField(
        upload_to="profiles/",
        blank=True,
        validators=[validate_image_upload],
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username}'s profile"
