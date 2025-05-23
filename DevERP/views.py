# DevERP/views.py
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Sum, Q
from django.utils import timezone
from datetime import datetime, timedelta
from django.contrib import messages

# In your DevERP/views.py

from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib import messages
from django.contrib.auth.models import User
from django.db.models import Q

def customer_login(request):
    """
    Custom login view that supports both username and email login
    """
    if request.user.is_authenticated:
        # If user is already logged in
        if request.user.is_staff:
            return redirect('adminside:dashboard')
        else:
            return redirect('inventory:inventory')
    
    if request.method == 'POST':
        username_or_email = request.POST.get('username', '').strip()
        password = request.POST.get('password')
        
        # Try to find user by username or email
        user = None
        
        # First try to authenticate with username
        user = authenticate(request, username=username_or_email, password=password)
        
        # If that fails, try to find user by email and authenticate
        if not user:
            try:
                # Check if input is an email
                user_obj = User.objects.get(email=username_or_email)
                user = authenticate(request, username=user_obj.username, password=password)
            except User.DoesNotExist:
                pass
        
        if user is not None:
            # Check if user is active
            if not user.is_active:
                messages.error(request, 'Your account has been deactivated. Please contact support.')
                return render(request, 'auth/login.html')  # Updated path
            
            # For customers, check their profile status
            if not user.is_staff and hasattr(user, 'customer_profile'):
                profile = user.customer_profile
                
                if profile.account_status == 'inactive':
                    messages.error(request, 'Your account is inactive. Please contact support.')
                    return render(request, 'auth/login.html')  # Updated path
                
                elif profile.account_status == 'suspended':
                    messages.error(request, 'Your account has been suspended. Please contact support.')
                    return render(request, 'auth/login.html')  # Updated path
                
                elif profile.account_status == 'pending':
                    messages.warning(request, 'Your account is pending approval. Please wait for activation.')
                    return render(request, 'auth/login.html')  # Updated path
            
            # Login successful
            login(request, user)
            
            # Redirect based on user type
            next_url = request.GET.get('next')
            if next_url:
                return redirect(next_url)
            elif user.is_staff:
                return redirect('adminside:dashboard')
            else:
                return redirect('inventory:inventory')
        else:
            messages.error(request, 'Invalid username/email or password.')
    
    return render(request, 'auth/login.html')  # Updated path

# Import your models with error handling
try:
    from inventory.models import Product, Category
except ImportError:
    Product = None
    Category = None

try:
    from orders.models import Order, OrderItem
except ImportError:
    Order = None
    OrderItem = None

@login_required
def dashboard_view(request):
    """Main dashboard view with key metrics"""
    context = {
        'title': 'Dashboard',
        'active_page': 'dashboard',
    }
    
    try:
        # Get date range for metrics (last 30 days)
        end_date = timezone.now()
        start_date = end_date - timedelta(days=30)
        
        # Basic inventory metrics
        if Product and Category:
            context['total_products'] = Product.objects.filter(is_active=True).count()
            context['low_stock_products'] = Product.objects.filter(
                stock_quantity__lte=10,
                is_active=True
            ).count()
            context['out_of_stock'] = Product.objects.filter(
                stock_quantity=0,
                is_active=True
            ).count()
            context['total_categories'] = Category.objects.filter(is_active=True).count()
        else:
            context['total_products'] = 0
            context['low_stock_products'] = 0
            context['out_of_stock'] = 0
            context['total_categories'] = 0
        
        # Order metrics (if Order model exists)
        if Order:
            try:
                context['total_orders'] = Order.objects.filter(
                    created_at__range=[start_date, end_date]
                ).count()
                context['pending_orders'] = Order.objects.filter(
                    status='pending',
                    created_at__range=[start_date, end_date]
                ).count()
                context['completed_orders'] = Order.objects.filter(
                    status='completed',
                    created_at__range=[start_date, end_date]
                ).count()
                
                # Revenue calculation
                revenue = Order.objects.filter(
                    status='completed',
                    created_at__range=[start_date, end_date]
                ).aggregate(total=Sum('total_amount'))['total'] or 0
                context['total_revenue'] = revenue
                
            except Exception:
                # If Order model doesn't exist yet
                context['total_orders'] = 0
                context['pending_orders'] = 0
                context['completed_orders'] = 0
                context['total_revenue'] = 0
        else:
            context['total_orders'] = 0
            context['pending_orders'] = 0
            context['completed_orders'] = 0
            context['total_revenue'] = 0
        
        # Recent activities
        if Product:
            context['recent_products'] = Product.objects.filter(
                is_active=True
            ).order_by('-created_at')[:5]
            
            # Low stock alerts
            context['low_stock_alerts'] = Product.objects.filter(
                stock_quantity__gt=0,
                stock_quantity__lte=10,
                is_active=True
            ).order_by('stock_quantity')[:10]
        else:
            context['recent_products'] = []
            context['low_stock_alerts'] = []
        
    except Exception as e:
        messages.error(request, f'Error loading dashboard data: {str(e)}')
        # Provide default values to prevent template errors
        context.update({
            'total_products': 0,
            'low_stock_products': 0,
            'out_of_stock': 0,
            'total_categories': 0,
            'total_orders': 0,
            'pending_orders': 0,
            'completed_orders': 0,
            'total_revenue': 0,
            'recent_products': [],
            'low_stock_alerts': [],
        })
    
    return render(request, 'adminside/dashboard.html', context)


def handler404(request, exception):
    """Custom 404 error page"""
    return render(request, '404.html', status=404)


def handler500(request):
    """Custom 500 error page"""
    return render(request, '500.html', status=500)


@login_required
def profile_view(request):
    """User profile view"""
    if request.method == 'POST':
        # Handle profile updates
        user = request.user
        user.first_name = request.POST.get('first_name', '').strip()
        user.last_name = request.POST.get('last_name', '').strip()
        user.email = request.POST.get('email', '').strip().lower()
        
        try:
            user.save()
            messages.success(request, 'Profile updated successfully!')
        except Exception as e:
            messages.error(request, f'Error updating profile: {str(e)}')
        
        return redirect('profile')
    
    return render(request, 'profile.html', {
        'title': 'My Profile',
        'active_page': 'profile',
    })


@login_required
def settings_view(request):
    """Application settings view"""
    return render(request, 'settings.html', {
        'title': 'Settings',
        'active_page': 'settings',
    })


# Additional utility views for DevERP

@login_required
def search_view(request):
    """Global search functionality"""
    query = request.GET.get('q', '').strip()
    results = {
        'products': [],
        'orders': [],
        'customers': [],
    }
    
    if query and len(query) >= 2:
        # Search products
        if Product:
            results['products'] = Product.objects.filter(
                Q(name__icontains=query) |
                Q(sku__icontains=query) |
                Q(barcode__icontains=query)
            ).filter(is_active=True)[:10]
        
        # Search orders
        if Order:
            results['orders'] = Order.objects.filter(
                Q(order_number__icontains=query) |
                Q(customer_name__icontains=query) |
                Q(customer_email__icontains=query)
            )[:10]
    
    return render(request, 'search_results.html', {
        'query': query,
        'results': results,
        'title': f'Search Results for "{query}"',
        'active_page': 'search',
    })


@login_required
def reports_view(request):
    """Reports dashboard"""
    context = {
        'title': 'Reports',
        'active_page': 'reports',
    }
    
    # Get report type from query params
    report_type = request.GET.get('type', 'sales')
    date_range = request.GET.get('range', '30')
    
    try:
        days = int(date_range)
    except ValueError:
        days = 30
    
    end_date = timezone.now()
    start_date = end_date - timedelta(days=days)
    
    context['report_type'] = report_type
    context['date_range'] = days
    context['start_date'] = start_date
    context['end_date'] = end_date
    
    if report_type == 'sales' and Order:
        # Sales report
        context['total_sales'] = Order.objects.filter(
            status='completed',
            created_at__range=[start_date, end_date]
        ).aggregate(total=Sum('total_amount'))['total'] or 0
        
        context['total_orders'] = Order.objects.filter(
            created_at__range=[start_date, end_date]
        ).count()
        
    elif report_type == 'inventory' and Product:
        # Inventory report
        context['total_stock_value'] = Product.objects.filter(
            is_active=True
        ).aggregate(
            total=Sum(models.F('stock_quantity') * models.F('cost_price'))
        )['total'] or 0
        
        context['low_stock_items'] = Product.objects.filter(
            stock_quantity__lte=models.F('reorder_level'),
            is_active=True
        ).count()
    
    return render(request, 'reports.html', context)


@login_required
def notifications_view(request):
    """User notifications"""
    notifications = []
    
    # Check for low stock alerts
    if Product:
        low_stock = Product.objects.filter(
            stock_quantity__lte=models.F('reorder_level'),
            stock_quantity__gt=0,
            is_active=True
        )[:5]
        
        for product in low_stock:
            notifications.append({
                'type': 'warning',
                'title': 'Low Stock Alert',
                'message': f'{product.name} has only {product.stock_quantity} units left',
                'link': f'/inventory/product/{product.id}/',
                'timestamp': timezone.now(),
            })
    
    # Check for pending orders
    if Order:
        pending_orders = Order.objects.filter(
            status='pending',
            created_at__gte=timezone.now() - timedelta(days=2)
        ).count()
        
        if pending_orders > 0:
            notifications.append({
                'type': 'info',
                'title': 'Pending Orders',
                'message': f'You have {pending_orders} pending orders to process',
                'link': '/orders/?status=pending',
                'timestamp': timezone.now(),
            })
    
    return render(request, 'notifications.html', {
        'notifications': notifications,
        'title': 'Notifications',
        'active_page': 'notifications',
    })


# API Views for AJAX requests
from django.http import JsonResponse

@login_required
def api_dashboard_stats(request):
    """API endpoint for dashboard statistics"""
    stats = {
        'products': 0,
        'orders': 0,
        'revenue': 0,
        'customers': 0,
    }
    
    try:
        if Product:
            stats['products'] = Product.objects.filter(is_active=True).count()
        
        if Order:
            # Last 30 days stats
            end_date = timezone.now()
            start_date = end_date - timedelta(days=30)
            
            stats['orders'] = Order.objects.filter(
                created_at__range=[start_date, end_date]
            ).count()
            
            revenue = Order.objects.filter(
                status='completed',
                created_at__range=[start_date, end_date]
            ).aggregate(total=Sum('total_amount'))['total']
            
            stats['revenue'] = float(revenue) if revenue else 0
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse(stats)


@login_required
def api_quick_stats(request):
    """API endpoint for quick statistics"""
    stats = {
        'low_stock': 0,
        'pending_orders': 0,
        'today_orders': 0,
        'today_revenue': 0,
    }
    
    try:
        if Product:
            stats['low_stock'] = Product.objects.filter(
                stock_quantity__lte=10,
                stock_quantity__gt=0,
                is_active=True
            ).count()
        
        if Order:
            today = timezone.now().date()
            
            stats['pending_orders'] = Order.objects.filter(
                status='pending'
            ).count()
            
            stats['today_orders'] = Order.objects.filter(
                created_at__date=today
            ).count()
            
            revenue = Order.objects.filter(
                status='completed',
                created_at__date=today
            ).aggregate(total=Sum('total_amount'))['total']
            
            stats['today_revenue'] = float(revenue) if revenue else 0
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse(stats)