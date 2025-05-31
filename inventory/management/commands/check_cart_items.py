# Create this file at: inventory/management/commands/check_cart_items.py

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from inventory.models import Cart, CartItem, MemoRequest
from orders.models import Order, OrderItem

User = get_user_model()

class Command(BaseCommand):
    help = 'Check cart items and orders in the database'

    def add_arguments(self, parser):
        parser.add_argument(
            '--user',
            type=str,
            help='Username or email to check',
        )

    def handle(self, *args, **options):
        username = options.get('user')
        
        if username:
            # Find user by username or email
            try:
                user = User.objects.get(username=username)
            except User.DoesNotExist:
                try:
                    user = User.objects.get(email=username)
                except User.DoesNotExist:
                    self.stdout.write(self.style.ERROR(f'User "{username}" not found'))
                    return
            
            users = [user]
        else:
            # Check all users
            users = User.objects.all()
        
        for user in users:
            self.stdout.write(self.style.SUCCESS(f'\n=== User: {user.username} ({user.email}) ==='))
            
            # Check cart
            try:
                cart = Cart.objects.get(user=user)
                self.stdout.write(f'\nCart ID: {cart.id}, Created: {cart.created_at}')
                
                # Check cart items
                cart_items = CartItem.objects.filter(cart=cart)
                if cart_items.exists():
                    self.stdout.write(f'\nCart Items ({cart_items.count()}):')
                    for item in cart_items:
                        self.stdout.write(
                            f'  - ID: {item.id}, Job: {item.job_no}, '
                            f'Design: {item.design_no}, Qty: {item.quantity}, '
                            f'Price: ${item.price}, Type: {item.item_type}, '
                            f'Added: {item.added_date}'
                        )
                else:
                    self.stdout.write('  No cart items')
                    
            except Cart.DoesNotExist:
                self.stdout.write('  No cart found')
            
            # Check memo requests
            memo_requests = MemoRequest.objects.filter(user=user)
            if memo_requests.exists():
                self.stdout.write(f'\nMemo Requests ({memo_requests.count()}):')
                for memo in memo_requests:
                    self.stdout.write(
                        f'  - ID: {memo.id}, Job: {memo.job_no}, '
                        f'Design: {memo.design_no}, Status: {memo.status}, '
                        f'Requested: {memo.requested_at}'
                    )
            
            # Check orders
            orders = Order.objects.filter(customer=user).order_by('-created_at')[:5]
            if orders.exists():
                self.stdout.write(f'\nRecent Orders ({orders.count()} shown):')
                for order in orders:
                    self.stdout.write(
                        f'  - Order: {order.order_number}, Status: {order.status}, '
                        f'Total: ${order.total_amount}, Created: {order.created_at}'
                    )
                    
                    # Show order items
                    order_items = OrderItem.objects.filter(order=order)
                    for item in order_items:
                        self.stdout.write(
                            f'    • {item.design_no} ({item.job_no}) - '
                            f'Type: {item.item_type}, Qty: {item.quantity}, '
                            f'Price: ${item.unit_price}'
                        )
            
            self.stdout.write('\n' + '-'*50)