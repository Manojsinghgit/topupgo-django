from django.db import models
from common.models import BaseModel


class Account(BaseModel):
    """User account with profile and contact details."""
    email = models.EmailField(unique=True)
    username = models.CharField(max_length=150, unique=True)
    phone_no = models.CharField(max_length=20, blank=True)
    profile_photo = models.ImageField(upload_to='profiles/', blank=True, null=True)
    first_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    is_verified = models.BooleanField(default=False)

    class Meta:
        db_table = 'account_account'
        ordering = ['-created_at']

    def __str__(self):
        return self.username
