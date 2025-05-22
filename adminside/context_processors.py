# adminside/context_processors.py
from orders.models import Order

def sidebar_context(request):
    """Add open orders count to context"""
    context = {}
    if request.user.is_authenticated:
        context['open_orders_count'] = Order.objects.filter(status='OPEN').count()
    return context