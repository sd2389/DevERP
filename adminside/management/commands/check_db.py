# adminside/management/commands/check_db.py
from django.core.management.base import BaseCommand
from django.db import connections
from django.db.utils import OperationalError

class Command(BaseCommand):
    help = "Check if the database is accessible"

    def handle(self, *args, **options):
        db_conn = connections['default']
        try:
            c = db_conn.cursor()
            self.stdout.write(self.style.SUCCESS('Successfully connected to the database!'))
            
            # Get some basic stats
            c.execute("SELECT COUNT(*) FROM orders_order")
            order_count = c.fetchone()[0]
            self.stdout.write(f"Order count: {order_count}")
            
            c.execute("SELECT COUNT(*) FROM inventory_inventoryitem")
            item_count = c.fetchone()[0]
            self.stdout.write(f"Inventory item count: {item_count}")
            
        except OperationalError as e:
            self.stdout.write(self.style.ERROR(f'Database connection failed: {e}'))