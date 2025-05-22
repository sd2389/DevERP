from django.db import models
from django.contrib.auth.models import User

class InventoryItem(models.Model):
    job_id        = models.CharField(max_length=50, unique=True)
    design_no     = models.CharField(max_length=50)
    job_no        = models.CharField(max_length=50)
    metal_type    = models.CharField(max_length=30)
    metal_quality = models.CharField(max_length=30)
    gwt           = models.DecimalField(max_digits=10, decimal_places=3)
    nwt           = models.DecimalField(max_digits=10, decimal_places=3)
    dwt           = models.DecimalField(max_digits=10, decimal_places=3)
    dpcs          = models.IntegerField()
    size          = models.CharField(max_length=20)
    memostock     = models.BooleanField()
    totamt        = models.DecimalField(max_digits=12, decimal_places=2)

    def __str__(self):
        return f"{self.design_no} ({self.job_no})"

class Category(models.Model):
    name = models.CharField(max_length=100)
    
    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name_plural = "Categories"
        
        
class Design(models.Model):
    design_no = models.CharField(max_length=20, unique=True)
    is_active = models.BooleanField(default=True)  # Admin visibility control
    
    # Additional fields from API
    category = models.CharField(max_length=100, blank=True)
    subcategory = models.CharField(max_length=100, blank=True)
    description = models.TextField(blank=True)
    image_base_path = models.CharField(max_length=255, blank=True)
    
    # Metadata fields
    last_synced = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.design_no
    
    class Meta:
        indexes = [
            models.Index(fields=['design_no']),
            models.Index(fields=['category']),
            models.Index(fields=['is_active']),
        ]
    
    
ORDER_STATUS_CHOICES = [
    ("Pending", "Pending"),
    ("In Process", "In Process"),
    ("Completed", "Completed"),
    ("Cancelled", "Cancelled"),
]


# This model represents a group of orders, which can contain multiple order types
class OrderGroup(models.Model):
    order_id = models.CharField(max_length=20, unique=True)
    customer = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=ORDER_STATUS_CHOICES, default="Pending")

    def __str__(self):
        return self.order_id


class InStockOrder(models.Model):
    order_group = models.ForeignKey(OrderGroup, on_delete=models.CASCADE)
    design_no = models.CharField(max_length=50)
    qty = models.PositiveIntegerField()
    status = models.CharField(max_length=20, choices=ORDER_STATUS_CHOICES, default="Pending")
    created_at = models.DateTimeField(auto_now_add=True)


class CustomOrder(models.Model):
    order_group = models.ForeignKey(OrderGroup, on_delete=models.CASCADE)
    design_no = models.CharField(max_length=50)
    custom_details = models.TextField(blank=True, null=True)
    qty = models.PositiveIntegerField()
    status = models.CharField(max_length=20, choices=ORDER_STATUS_CHOICES, default="Pending")
    created_at = models.DateTimeField(auto_now_add=True)


class RequestOrder(models.Model):
    order_group = models.ForeignKey(OrderGroup, on_delete=models.CASCADE)
    design_no = models.CharField(max_length=50)
    qty = models.PositiveIntegerField()
    status = models.CharField(max_length=20, choices=ORDER_STATUS_CHOICES, default="Pending")
    created_at = models.DateTimeField(auto_now_add=True)
