from django.db import models
from django.conf import settings


class HirerProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='hirer_profile')
    full_name = models.CharField(max_length=100)
    company_name = models.CharField(max_length=100, blank=True)
    photo = models.ImageField(upload_to='hirers/photos/', blank=True, null=True)

    # Location
    village_town = models.CharField(max_length=100)
    district = models.CharField(max_length=100)
    state = models.CharField(max_length=50)
    pincode = models.CharField(max_length=6)
    full_address = models.TextField()

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.full_name or self.user.email
