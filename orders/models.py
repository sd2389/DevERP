from django.db import models
from django.conf import settings
from inventory.models import InventoryItem # Assuming InventoryItem is in inventory/models.py

class Order(models.Model):
    STATUS_CHOICES = [
        ('OPEN', 'Open'),
        ('IN_PROCESS', 'In Process'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
    ]
    
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=12,
        choices=STATUS_CHOICES,
        default='OPEN'
    )
    
    def __str__(self):
        return f"Order #{self.id} – {self.customer}"

class OrderItem(models.Model):
    order           = models.ForeignKey(
        Order,
        related_name='items',
        on_delete=models.CASCADE
    )
    inventory_item  = models.ForeignKey(
        InventoryItem,
        on_delete=models.CASCADE
    )
    quantity        = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"{self.quantity}×{self.inventory_item} in Order #{self.order.id}"


class InstockOrder(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    design_no = models.CharField(max_length=100)
    qty = models.PositiveIntegerField(default=1)
    status = models.CharField(max_length=20, choices=Order.STATUS_CHOICES, default='OPEN')

    def __str__(self):
        return f"Instock: {self.design_no} (x{self.qty}) – Order #{self.order.id}"


class RequestOrder(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    design_no = models.CharField(max_length=100)
    qty = models.PositiveIntegerField(default=1)
    status = models.CharField(max_length=20, choices=Order.STATUS_CHOICES, default='OPEN')

    def __str__(self):
        return f"Requested: {self.design_no} (x{self.qty}) – Order #{self.order.id}"


class CustomOrder(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    design_no = models.CharField(max_length=100)
    qty = models.PositiveIntegerField(default=1)
    status = models.CharField(max_length=20, choices=Order.STATUS_CHOICES, default='OPEN')

    def __str__(self):
        return f"Custom: {self.design_no} (x{self.qty}) – Order #{self.order.id}"
