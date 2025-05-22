# orders/admin.py

from django.contrib import admin
from django.db.models import Sum
from .models import Order, OrderItem
from inventory.models import InventoryItem

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display   = ('id','customer','status','created_at','item_count')
    list_filter    = ('status','created_at')
    list_editable  = ('status',)
    ordering       = ('-created_at',)
    actions        = ('mark_completed',)

    def item_count(self, obj):
        return obj.items.aggregate(total=Sum('quantity'))['total'] or 0
    item_count.short_description = 'Total Items'

    def mark_completed(self, request, queryset):
        updated = queryset.update(status='COMPLETED')
        self.message_user(request, f"{updated} order(s) marked completed.")
    mark_completed.short_description = "Mark selected orders as Completed"


@admin.register(InventoryItem)
class InventoryItemAdmin(admin.ModelAdmin):
    list_display = ('design_no', 'job_no', 'qty_ordered')
    # remove the invalid ordering line here!

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # annotate with total sold and order by it descending
        return (
            qs
            .annotate(_qty_sold=Sum('orderitem__quantity'))
            .order_by('-_qty_sold', 'design_no')  # fallback by design_no
        )

    def qty_ordered(self, obj):
        return obj._qty_sold or 0
    qty_ordered.admin_order_field = '_qty_sold'
    qty_ordered.short_description = 'Qty Sold'
