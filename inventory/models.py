# inventory/models.py
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.validators import MinValueValidator
from decimal import Decimal
from django.conf import settings

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
    """Product category model"""
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True, null=True, blank=True)
    description = models.TextField(blank=True)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='children')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Category'
        verbose_name_plural = 'Categories'
        ordering = ['name']
    
    def __str__(self):
        return self.name
    
    def get_absolute_url(self):
        return f'/inventory/category/{self.slug}/'


class Supplier(models.Model):
    """Supplier/Vendor model"""
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=50, unique=True)
    contact_person = models.CharField(max_length=100, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, default='USA')
    postal_code = models.CharField(max_length=20, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} ({self.code})"


class Product(models.Model):
    """Product model"""
    # Basic Information
    name = models.CharField(max_length=200)
    sku = models.CharField(max_length=100, unique=True, help_text="Stock Keeping Unit")
    barcode = models.CharField(max_length=100, blank=True, unique=True, null=True)
    description = models.TextField(blank=True)
    
    # Categorization
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name='products')
    
    # Pricing
    cost_price = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Cost price from supplier"
    )
    selling_price = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Selling price to customers"
    )
    
    # Inventory
    stock_quantity = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    reorder_level = models.IntegerField(
        default=10, 
        validators=[MinValueValidator(0)],
        help_text="Minimum stock level before reorder"
    )
    reorder_quantity = models.IntegerField(
        default=50,
        validators=[MinValueValidator(1)],
        help_text="Quantity to order when stock is low"
    )
    
    # Supplier Information
    supplier = models.ForeignKey(Supplier, on_delete=models.SET_NULL, null=True, blank=True, related_name='products')
    
    # Physical Attributes
    weight = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True, help_text="Weight in kg")
    dimensions = models.CharField(max_length=100, blank=True, help_text="L x W x H")
    
    # Status
    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='products_created')
    
    class Meta:
        ordering = ['name']
        indexes = [
            models.Index(fields=['sku']),
            models.Index(fields=['barcode']),
            models.Index(fields=['stock_quantity']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.sku})"
    
    @property
    def is_in_stock(self):
        return self.stock_quantity > 0
    
    @property
    def is_low_stock(self):
        return 0 < self.stock_quantity <= self.reorder_level
    
    @property
    def profit_margin(self):
        if self.cost_price > 0:
            return ((self.selling_price - self.cost_price) / self.cost_price) * 100
        return 0
    
    def get_absolute_url(self):
        return f'/inventory/product/{self.id}/'


class Design(models.Model):
    design_no = models.CharField(max_length=50, unique=True)
    is_active = models.BooleanField(default=True)  # Admin visibility control
    
    # Additional fields from API
    category = models.CharField(max_length=100, blank=True)
    subcategory = models.CharField(max_length=100, blank=True)
    description = models.TextField(blank=True)
    image_base_path = models.CharField(max_length=255, blank=True)
    gender = models.CharField(max_length=50, blank=True, db_index=True)
    collection = models.CharField(max_length=100, blank=True, db_index=True)
    product_type = models.CharField(max_length=100, blank=True, db_index=True)
    
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
            models.Index(fields=['gender']),
            models.Index(fields=['collection']),
            models.Index(fields=['product_type']),
            models.Index(fields=['subcategory']),
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
    customer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='order_groups')
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=ORDER_STATUS_CHOICES, default="Pending")

    def __str__(self):
        return self.order_id


class InStockOrder(models.Model):
    order_group = models.ForeignKey(OrderGroup, on_delete=models.CASCADE, related_name='in_stock_orders')
    design_no = models.CharField(max_length=50)
    qty = models.PositiveIntegerField()
    status = models.CharField(max_length=20, choices=ORDER_STATUS_CHOICES, default="Pending")
    created_at = models.DateTimeField(auto_now_add=True)


class CustomOrder(models.Model):
    order_group = models.ForeignKey(OrderGroup, on_delete=models.CASCADE, related_name='custom_orders')
    design_no = models.CharField(max_length=50)
    custom_details = models.TextField(blank=True, null=True)
    qty = models.PositiveIntegerField()
    status = models.CharField(max_length=20, choices=ORDER_STATUS_CHOICES, default="Pending")
    created_at = models.DateTimeField(auto_now_add=True)


class RequestOrder(models.Model):
    order_group = models.ForeignKey(OrderGroup, on_delete=models.CASCADE, related_name='request_orders')
    design_no = models.CharField(max_length=50)
    qty = models.PositiveIntegerField()
    status = models.CharField(max_length=20, choices=ORDER_STATUS_CHOICES, default="Pending")
    created_at = models.DateTimeField(auto_now_add=True)


class UserProfile(models.Model):
    """
    Extended user profile to store additional information
    """
    ACCOUNT_TYPES = (
        ('Retailer', 'Retailer'),
        ('Wholesaler', 'Wholesaler'),
        ('Manufacturer', 'Manufacturer'),
    )
    
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='profile')
    phone = models.CharField(max_length=20, blank=True, null=True)
    account_type = models.CharField(max_length=20, choices=ACCOUNT_TYPES, default='Retailer')
    business_name = models.CharField(max_length=255, blank=True, null=True)
    business_address = models.TextField(blank=True, null=True)
    whatsapp_phone = models.CharField(max_length=20, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    activated_at = models.DateTimeField(null=True, blank=True)
    deactivated_at = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.user.username}'s Profile"


class StockMovement(models.Model):
    """Track all stock movements (in/out)"""
    MOVEMENT_TYPES = [
        ('IN', 'Stock In'),
        ('OUT', 'Stock Out'),
        ('ADJUST', 'Adjustment'),
        ('RETURN', 'Return'),
        ('DAMAGED', 'Damaged'),
    ]
    
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='stock_movements')
    movement_type = models.CharField(max_length=10, choices=MOVEMENT_TYPES)
    quantity = models.IntegerField()
    reference_number = models.CharField(max_length=100, blank=True, help_text="PO number, Invoice number, etc.")
    notes = models.TextField(blank=True)
    
    # Track before and after quantities
    quantity_before = models.IntegerField()
    quantity_after = models.IntegerField()
    
    # User tracking
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='stock_movements_created')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.movement_type} - {self.product.name} ({self.quantity})"
    
    def save(self, *args, **kwargs):
        # Auto-calculate quantity_after if not set
        if not self.pk and not self.quantity_after:
            self.quantity_before = self.product.stock_quantity
            if self.movement_type in ['IN', 'RETURN']:
                self.quantity_after = self.quantity_before + self.quantity
            else:
                self.quantity_after = self.quantity_before - self.quantity
        super().save(*args, **kwargs)


class ProductImage(models.Model):
    """Product images"""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='products/%Y/%m/')
    alt_text = models.CharField(max_length=200, blank=True)
    is_primary = models.BooleanField(default=False)
    display_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['display_order', '-is_primary']
    
    def __str__(self):
        return f"Image for {self.product.name}"
    
    def save(self, *args, **kwargs):
        # Ensure only one primary image per product
        if self.is_primary:
            ProductImage.objects.filter(product=self.product, is_primary=True).update(is_primary=False)
        super().save(*args, **kwargs)


# Create a UserProfile when a User is created
@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)

@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def save_user_profile(sender, instance, **kwargs):
    if not hasattr(instance, 'profile'):
        UserProfile.objects.create(user=instance)
    instance.profile.save()
    
class Wishlist(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='wishlist_items'
    )
    design_no = models.CharField(max_length=50)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'inventory_wishlist'
        unique_together = ('user', 'design_no')
        managed = False     # tells Django “the table already exists—don’t try to create or delete it”

class Cart(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='carts')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    design_no = models.CharField(max_length=50)
    job_no = models.CharField(max_length=50)
    metal_type = models.CharField(max_length=30)
    metal_quality = models.CharField(max_length=30)
    metal_color = models.CharField(max_length=30, blank=True, null=True)
    diamond_quality = models.CharField(max_length=30, blank=True, null=True)
    diamond_color = models.CharField(max_length=30, blank=True, null=True)
    gwt = models.DecimalField(max_digits=10, decimal_places=3)
    nwt = models.DecimalField(max_digits=10, decimal_places=3)
    dwt = models.DecimalField(max_digits=10, decimal_places=3)
    pcs = models.IntegerField(default=1)
    size = models.CharField(max_length=20)
    totamt = models.DecimalField(max_digits=12, decimal_places=2)
    item_type = models.CharField(max_length=10, choices=[('stock', 'Stock'), ('memo', 'Memo'), ('custom', 'Custom')])
    custom_remark = models.TextField(blank=True, null=True)
    added_at = models.DateTimeField(auto_now_add=True)
