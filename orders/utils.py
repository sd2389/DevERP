# orders/utils.py
import re
from django.db import transaction
from orders.models import Order, OrderItem

def get_next_custom_job_no():
    all_custom = OrderItem.objects.filter(job_no__startswith='custom').values_list('job_no', flat=True)
    max_num = 0
    for job_no in all_custom:
        match = re.match(r'custom(\d+)', job_no)
        if match:
            num = int(match.group(1))
            if num > max_num:
                max_num = num
    return f'custom{max_num + 1}'

def get_next_order_number():
    """Generate the next order number in sequence"""
    with transaction.atomic():
        # Lock the orders table to prevent race conditions
        orders = Order.objects.select_for_update().filter(
            order_number__regex=r'^ORD\d+$'
        ).order_by('-id')
        
        max_num = 0
        
        # Find the highest number
        for order in orders[:100]:  # Check last 100 orders for performance
            try:
                num = int(order.order_number.replace('ORD', ''))
                if num > max_num:
                    max_num = num
            except ValueError:
                continue
        
        # Start from max + 1
        next_num = max_num + 1
        
        # Keep incrementing until we find an unused number
        while True:
            order_number = f"ORD{next_num}"
            if not Order.objects.filter(order_number=order_number).exists():
                return order_number
            next_num += 1