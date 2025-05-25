# accounts/models.py

from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    username = models.EmailField('email address', unique=True)
    full_name = models.CharField(max_length=255)
    mobile_no = models.CharField(max_length=15)
    company_name = models.CharField(max_length=255)
    address = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    country = models.CharField(max_length=100)
    zip_code = models.CharField(max_length=20)
    gst_no = models.CharField(max_length=30, blank=True, null=True)
    pan_no = models.CharField(max_length=30, blank=True, null=True)

    REQUIRED_FIELDS = ['full_name', 'mobile_no', 'company_name', 'address', 'city', 'state', 'country', 'zip_code']

    USERNAME_FIELD = 'username'  # Email is used for login

    def __str__(self):
        return self.username
