# orders/management/commands/sync_order_sequence.py
from django.core.management.base import BaseCommand
from orders.models import Order, OrderSequence
import re

class Command(BaseCommand):
    help = 'Sync order sequence with existing orders'

    def handle(self, *args, **options):
        # Find the highest order number
        orders = Order.objects.filter(
            order_number__regex=r'^ORD\d+$'
        ).order_by('-id')
        
        max_num = 0
        for order in orders:
            try:
                num = int(order.order_number.replace('ORD', ''))
                if num > max_num:
                    max_num = num
                    self.stdout.write(f"Found order: {order.order_number}")
            except ValueError:
                pass
        
        # Update or create sequence
        seq, created = OrderSequence.objects.get_or_create(id=1)
        seq.last_number = max_num
        seq.save()
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully synced order sequence. Last number: {max_num}'
            )
        )