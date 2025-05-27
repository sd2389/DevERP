# adminside/models.py
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from django.conf import settings


# Extend User model with customer profile
class CustomerProfile(models.Model):
    """Extended customer profile information"""
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='customer_profile')
    phone = models.CharField(max_length=20, blank=True)
    company = models.CharField(max_length=100, blank=True)
    address_line1 = models.CharField(max_length=255, blank=True)
    address_line2 = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    postal_code = models.CharField(max_length=20, blank=True)
    country = models.CharField(max_length=100, blank=True)
    
    # Business information
    tax_id = models.CharField(max_length=50, blank=True)
    business_type = models.CharField(max_length=50, choices=[
        ('retail', 'Retail'),
        ('wholesale', 'Wholesale'),
        ('distributor', 'Distributor'),
        ('other', 'Other')
    ], default='retail')
    
    # Account status and tracking
    account_status = models.CharField(max_length=20, choices=[
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('suspended', 'Suspended'),
        ('pending', 'Pending Approval')
    ], default='pending')
    
    deactivated_at = models.DateTimeField(null=True, blank=True)
    deactivated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='deactivated_customers')
    deactivation_reason = models.TextField(blank=True)
    
    # Customer metrics
    total_orders = models.IntegerField(default=0)
    total_spent = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    last_order_date = models.DateTimeField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Customer Profile'
        verbose_name_plural = 'Customer Profiles'
    
    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} - {self.account_status}"
    
    @property
    def is_active_customer(self):
        """Check if customer can login and place orders"""
        return self.user.is_active and self.account_status == 'active'

# Signal to create customer profile automatically
@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_customer_profile(sender, instance, created, **kwargs):
    if created and not instance.is_staff:
        CustomerProfile.objects.create(user=instance)

@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def save_customer_profile(sender, instance, **kwargs):
    if hasattr(instance, 'customer_profile'):
        instance.customer_profile.save()

# Existing models (keep these)
class ActivityLog(models.Model):
    """Track admin user activities in the system"""
    ACTION_CHOICES = (
        ('CREATE', 'Created'),
        ('UPDATE', 'Updated'),
        ('DELETE', 'Deleted'),
        ('LOGIN', 'Logged in'),
        ('LOGOUT', 'Logged out'),
        ('ACTIVATE', 'Activated'),
        ('DEACTIVATE', 'Deactivated'),
    )
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='activities')
    action = models.CharField(max_length=10, choices=ACTION_CHOICES)
    target_model = models.CharField(max_length=50)
    target_id = models.IntegerField(null=True, blank=True)
    details = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-timestamp']
        verbose_name = 'Activity Log'
        verbose_name_plural = 'Activity Logs'
    
    def __str__(self):
        return f"{self.user.username} {self.get_action_display().lower()} {self.target_model}"


class SystemSetting(models.Model):
    """Store system-wide settings for the admin panel"""
    key = models.CharField(max_length=50, unique=True)
    value = models.TextField()
    description = models.TextField(blank=True)
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='updated_settings')
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.key