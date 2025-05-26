# orders/models.py
from django.db import models
from django.conf import settings
from django.utils import timezone

class Customer(models.Model):
    """Customer model"""
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    # For customers without user accounts
    name = models.CharField(max_length=200)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    
    # Address
    address_line1 = models.CharField(max_length=255)
    address_line2 = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    country = models.CharField(max_length=100, default='USA')
    postal_code = models.CharField(max_length=20)
    
    # Additional info
    company_name = models.CharField(max_length=200, blank=True)
    tax_id = models.CharField(max_length=50, blank=True)
    notes = models.TextField(blank=True)
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
    
    def __str__(self):
        return self.name


class Order(models.Model):
    """Order model"""
    ORDER_STATUS = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('refunded', 'Refunded'),
    ]
    
    PAYMENT_STATUS = [
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('partial', 'Partial'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ]
    
    PAYMENT_METHODS = [
        ('cash', 'Cash'),
        ('card', 'Credit/Debit Card'),
        ('bank_transfer', 'Bank Transfer'),
        ('check', 'Check'),
        ('other', 'Other'),
    ]
    
    # Order identification
    order_number = models.CharField(max_length=50, unique=True)
    order_id = models.CharField(max_length=50, unique=True)
    
    # Customer information
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name='orders', null=True, blank=True)
    # For guest checkouts
    customer_name = models.CharField(max_length=200)
    customer_email = models.EmailField()
    customer_phone = models.CharField(max_length=20)
    
    # Shipping information
    shipping_name = models.CharField(max_length=255, default='')
    shipping_email = models.EmailField(default='')
    shipping_phone = models.CharField(max_length=20, default='')
    
    # Shipping address
    shipping_address_line1 = models.CharField(max_length=255)
    shipping_address_line2 = models.CharField(max_length=255, blank=True)
    shipping_city = models.CharField(max_length=100)
    shipping_state = models.CharField(max_length=100)
    shipping_country = models.CharField(max_length=100, default='USA')
    shipping_postal_code = models.CharField(max_length=20)
    
    # Order details
    status = models.CharField(max_length=20, choices=ORDER_STATUS, default='pending')
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS, default='pending')
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS, blank=True)
    
    # Amounts
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    shipping_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    shipping_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Additional information
    notes = models.TextField(blank=True)
    internal_notes = models.TextField(blank=True, help_text="Not visible to customers")
    customer_notes = models.TextField(blank=True, default='')
    admin_notes = models.TextField(blank=True, default='')
    
    # Tracking
    tracking_number = models.CharField(max_length=100, blank=True)
    shipped_date = models.DateTimeField(null=True, blank=True)
    delivered_date = models.DateTimeField(null=True, blank=True)
    
    # Additional timestamps
    processed_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='orders_created')
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Order {self.order_number}"
    
    def save(self, *args, **kwargs):
        # Generate order number if not set
        if not self.order_number:
            self.order_number = self.generate_order_number()
        
        # Set order_id same as order_number if not set
        if not self.order_id:
            self.order_id = self.order_number
            
        # Copy shipping_cost to shipping_amount for compatibility
        if self.shipping_cost and not self.shipping_amount:
            self.shipping_amount = self.shipping_cost
        
        # Calculate total if not set
        if not self.total_amount:
            self.calculate_totals()
        
        super().save(*args, **kwargs)
    
    def generate_order_number(self):
        """Generate unique order number"""
        import random
        import string
        timestamp = timezone.now().strftime('%Y%m%d%H%M%S')
        random_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
        return f"ORD-{timestamp}-{random_str}"
    
    def calculate_totals(self):
        """Calculate order totals"""
        # This will be updated when OrderItem is saved
        self.total_amount = self.subtotal + self.tax_amount + self.shipping_cost - self.discount_amount


# orders/models.py - Update the OrderItem model

class OrderItem(models.Model):
    """Order line items"""
    ITEM_TYPES = [
        ('stock', 'Stock Item'),
        ('memo', 'Memo Request'),
        ('custom', 'Custom Order'),
    ]
    
    ITEM_STATUS = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('processing', 'Processing'),
        ('ready', 'Ready'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    ]
    
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    
    # Product identification
    product_id = models.IntegerField(default=0)
    product_name = models.CharField(max_length=255)
    product_sku = models.CharField(max_length=100, default='')
    design_no = models.CharField(max_length=50, default='')
    job_no = models.CharField(max_length=50, default='')
    
    # Item type and status
    item_type = models.CharField(max_length=20, choices=ITEM_TYPES, default='stock')
    item_status = models.CharField(max_length=30, choices=ITEM_STATUS, default='pending')
    status_updated_at = models.DateTimeField(auto_now=True)
    
    # Metal specifications
    metal_type = models.CharField(max_length=50, default='')
    metal_quality = models.CharField(max_length=20, default='')
    metal_color = models.CharField(max_length=20, default='')
    
    # Diamond specifications
    diamond_quality = models.CharField(max_length=20, default='')
    diamond_color = models.CharField(max_length=20, default='')
    
    # Weight and size
    gwt = models.DecimalField(max_digits=8, decimal_places=3, null=True, blank=True)
    dwt = models.DecimalField(max_digits=8, decimal_places=3, null=True, blank=True)
    nwt = models.DecimalField(max_digits=8, decimal_places=3, null=True, blank=True)
    size = models.CharField(max_length=20, default='')
    
    # Quantities and pricing
    quantity = models.IntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Memo specific fields
    memo_requested_at = models.DateTimeField(null=True, blank=True)
    memo_approved_at = models.DateTimeField(null=True, blank=True)
    memo_return_date = models.DateField(null=True, blank=True)
    
    # Custom order remarks
    custom_remarks = models.TextField(blank=True, default='')
    
    # Cancellation
    is_cancelled = models.BooleanField(default=False)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['order', 'item_type']),
            models.Index(fields=['design_no', 'job_no']),
        ]
    
    def __str__(self):
        return f"{self.product_name} x {self.quantity}"
    
    def save(self, *args, **kwargs):
        # Calculate total
        self.total = (self.unit_price * self.quantity) - self.discount_amount
        super().save(*args, **kwargs)

class Payment(models.Model):
    """Payment records"""
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=20, choices=Order.PAYMENT_METHODS)
    
    # Transaction details
    transaction_id = models.CharField(max_length=100, blank=True)
    reference_number = models.CharField(max_length=100, blank=True)
    
    # Status
    is_successful = models.BooleanField(default=True)
    failure_reason = models.CharField(max_length=255, blank=True)
    
    # Additional info
    notes = models.TextField(blank=True)
    
    # Timestamps
    payment_date = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    
    class Meta:
        ordering = ['-payment_date']
    
    def __str__(self):
        return f"Payment {self.amount} for Order {self.order.order_number}"