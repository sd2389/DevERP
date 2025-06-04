from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.admin.views.decorators import staff_member_required
from django.views.decorators.http import require_POST, require_GET
from django.contrib.auth.forms import PasswordResetForm
from django.contrib.auth import authenticate, login, get_user_model
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Sum, Q, Count
from django.utils import timezone

# Local imports
from .decorators import admin_login_required
from .models import CustomerProfile, ActivityLog
from accounts.models import PasswordResetRequest, User
from orders.models import Order
from inventory.models import Design

# Python standard library
import json
import logging
import csv
from datetime import datetime, timedelta

# Setup logger
logger = logging.getLogger('adminside')
User = get_user_model()

def admin_login(request):
    """
    Custom login view for adminside app.
    Redirects to the adminside dashboard on successful login.
    """
    # If user is already logged in, redirect to dashboard
    if request.user.is_authenticated:
        return redirect('dashboard')
        
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        user = authenticate(request, username=username, password=password)
        
        if user is not None and user.is_staff:  # Only staff users can access admin
            login(request, user)
            
            # Redirect to the next URL if provided, otherwise to dashboard
            next_url = request.GET.get('next', 'dashboard')
            return redirect(next_url)
        else:
            messages.error(request, 'Invalid username or password, or insufficient permissions.')
    
    return render(request, 'adminside/login.html')

def admin_logout(request):
    logout(request)
    return redirect('adminside:admin_login') 

@login_required
def activity_log(request):
    activities = ActivityLog.objects.all().order_by('-timestamp')[:100]
    return render(request, 'adminside/activity_log.html', {'activities': activities})


# Define admin check function
def is_admin(user):
    """Check if the user is an admin"""
    return user.is_staff or user.is_superuser

# @login_required
# @user_passes_test(is_admin)
def dashboard(request):
    try:
        # Import Order model
        from orders.models import Order
        # Calculate statistics
        total_orders = Order.objects.count()
        pending_orders = Order.objects.filter(status__in=['pending', 'Pending', 'PENDING']).count()
        completed_orders = Order.objects.filter(status__in=['completed', 'Completed', 'COMPLETED']).count()
        memo_requests = Order.objects.filter(status__in=['memo', 'on memo', 'MEMO', 'ON MEMO']).count()  # Adjust if your order_type field is different

        # Total revenue from completed orders
        total_revenue = Order.objects.filter(
            status__in=['completed', 'Completed', 'COMPLETED']
        ).aggregate(
            total=Sum('total_amount')
        )['total'] or 0

        # Recent orders (last 10)
        recent_orders = Order.objects.select_related('customer').order_by('-created_at')[:10]

        # Order status distribution for pie chart
        order_status_counts = Order.objects.values('status').annotate(
            count=Count('id')
        ).order_by('status')
        order_status_data = {}
        for item in order_status_counts:
            status = item['status'] or 'Unknown'
            order_status_data[status] = item['count']

        # Order trends for last 30 days
        thirty_days_ago = timezone.now() - timedelta(days=30)
        order_trends = Order.objects.filter(
            created_at__gte=thirty_days_ago
        ).extra(
            select={'day': 'date(created_at)'}
        ).values('day').annotate(
            count=Count('id')
        ).order_by('day')
        trends_labels = []
        trends_values = []
        current_date = thirty_days_ago.date()
        end_date = timezone.now().date()
        trends_dict = {item['day']: item['count'] for item in order_trends}
        while current_date <= end_date:
            trends_labels.append(current_date.strftime('%m/%d'))
            trends_values.append(trends_dict.get(str(current_date), 0) if str(current_date) in trends_dict else 0)
            current_date += timedelta(days=1)
        order_trends_data = {
            'labels': trends_labels,
            'values': trends_values
        }

        # Active customers (non-staff users)
        active_customers = User.objects.filter(
            is_staff=False,
            is_active=True
        ).count()

        # Recent activities
        recent_activities = ActivityLog.objects.select_related('user').order_by('-timestamp')[:10]

        # All orders for the modal (serialize as JSON)
        all_orders = Order.objects.select_related('customer').all().order_by('-created_at')[:200]
        all_orders_json = []
        for order in all_orders:
            all_orders_json.append({
                "order_id": order.order_id,
                "created_at": order.created_at.isoformat(),
                "customer_name": order.customer.get_full_name() if hasattr(order.customer, 'get_full_name') else str(order.customer),
                "item_count": getattr(order, "items_count", None) or 0,  # you may need to adjust this field
                "total_amount": float(order.total_amount) if order.total_amount else 0,
                "status": order.status,
            })

        open_orders_count = pending_orders

        context = {
            'page_title': 'Dashboard',
            'total_orders': total_orders,
            'pending_orders': pending_orders,
            'completed_orders': completed_orders,
            'memo_requests': memo_requests,
            'total_revenue': total_revenue,
            'active_customers': active_customers,
            'recent_orders': recent_orders,
            'recent_activities': recent_activities,
            'order_status_data': json.dumps(order_status_data),
            'order_trends_data': json.dumps(order_trends_data),
            'open_orders_count': open_orders_count,
            'all_orders_json': json.dumps(all_orders_json),
        }
        return render(request, 'adminside/dashboard.html', context)
    except Exception as e:
        # ... your existing except block is fine ...
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error loading dashboard: {str(e)}")
        context = {
            'page_title': 'Dashboard',
            'total_orders': 0,
            'pending_orders': 0,
            'completed_orders': 0,
            'memo_requests': 0,
            'total_revenue': 0,
            'active_customers': 0,
            'recent_orders': [],
            'recent_activities': [],
            'order_status_data': json.dumps({}),
            'order_trends_data': json.dumps({'labels': [], 'values': []}),
            'open_orders_count': 0,
            'all_orders_json': json.dumps([]),
        }
        return render(request, 'adminside/dashboard.html', context)

def staff_required(user):
    return user.is_staff

# @user_passes_test(staff_required)
def design_list(request):
    designs = Design.objects.all().order_by('design_no')
    return render(request, 'adminside/design_list.html', { 'designs': designs })

# @user_passes_test(staff_required)
def toggle_design(request, pk):
    d = get_object_or_404(Design, pk=pk)
    d.is_active = not d.is_active
    d.save()
    return redirect('adminside:design_list')


# @login_required
# @user_passes_test(is_admin)
def orders_list(request):
    """
    Admin view for listing all orders with filtering and pagination.
    """
    try:
        # In a real app, fetch orders from database
        # For demo, just render the template
        
        # Get filter parameters
        status = request.GET.get('status', '')
        search = request.GET.get('search', '')
        
        # Render orders list template
        return render(request, 'adminside/orders.html')
    except Exception as e:
        logger.error(f"Error rendering admin orders list: {str(e)}")
        messages.error(request, f"Error loading orders: {str(e)}")
        return render(request, 'adminside/error.html', {'error': str(e)})

# @login_required
# @user_passes_test(is_admin)
def order_detail(request, order_id):
    """
    Admin view for viewing and managing a specific order.
    """
    try:
        # In a real app, fetch order details from database
        # For demo, just render the template with mock data
        order = {
            'order_id': order_id,
            'date': datetime.now().isoformat(),
            'status': 'Pending',
            'items': {
                'stock': [],
                'memo': [],
                'custom': []
            },
            'customer': {
                'name': 'John Doe',
                'email': 'john.doe@example.com',
                'phone': '(123) 456-7890'
            },
            'payment': {
                'subtotal': 1000.00,
                'shipping': 9.99,
                'tax': 80.00,
                'discount': 0.00,
                'total': 1089.99
            },
            'shipping_address': {
                'line1': '123 Main St',
                'line2': 'Apt 4B',
                'city': 'New York',
                'state': 'NY',
                'postal_code': '10001',
                'country': 'US'
            }
        }
        
        return render(request, 'adminside/order_detail.html', {'order': order})
    except Exception as e:
        logger.error(f"Error rendering admin order detail: {str(e)}")
        messages.error(request, f"Error loading order details: {str(e)}")
        return redirect('adminside:orders')

# @login_required
# @user_passes_test(is_admin)
@require_POST
def update_order(request, order_id):
    """
    Admin view for updating order status and details.
    """
    try:
        # Get new status from form
        new_status = request.POST.get('status')
        
        # In a real app, update order in database
        # For demo, just show success message
        
        messages.success(request, f"Order {order_id} status updated to {new_status}")
        return redirect('adminside:order_detail', order_id=order_id)
    except Exception as e:
        logger.error(f"Error updating order {order_id}: {str(e)}")
        messages.error(request, f"Error updating order: {str(e)}")
        return redirect('adminside:order_detail', order_id=order_id)

# @login_required
# @user_passes_test(is_admin)
@require_POST
def send_order_emails(request, order_id):
    """
    Admin view for manually sending order emails.
    """
    try:
        # In a real app, retrieve the order from the database
        # For demonstration, we'll use a mock order object
        order = {
            'order_id': order_id,
            'date': datetime.now().isoformat(),
            'status': 'Pending',
            'items': {
                'stock': [],
                'memo': [],
                'custom': []
            },
            'customer': {
                'name': 'John Doe',
                'email': 'john.doe@example.com',
                'phone': '(123) 456-7890'
            },
            'payment': {
                'subtotal': 1000.00,
                'shipping': 9.99,
                'tax': 80.00,
                'discount': 0.00,
                'total': 1089.99
            },
            'shipping_address': {
                'line1': '123 Main St',
                'line2': 'Apt 4B',
                'city': 'New York',
                'state': 'NY',
                'postal_code': '10001',
                'country': 'US'
            }
        }
        
        # Get email recipients
        customer_email = 'john.doe@example.com'  # In a real app, get from order
        
        # Check which emails to send
        send_to_customer = request.POST.get('send_to_customer') == 'on'
        send_to_admin = request.POST.get('send_to_admin') == 'on'
        
        success_messages = []
        error_messages = []
        
        # Send customer email if requested
        if send_to_customer:
            try:
                # For demo, we'll just simulate success
                customer_email_sent = True
                if customer_email_sent:
                    success_messages.append(f"Confirmation email sent to {customer_email}")
                else:
                    error_messages.append(f"Failed to send confirmation email to {customer_email}")
            except Exception as e:
                logger.error(f"Error sending customer email: {str(e)}")
                error_messages.append(f"Error sending customer email: {str(e)}")
        
        # Send admin email if requested
        if send_to_admin:
            try:
                # For demo, we'll just simulate success
                admin_email_sent = True
                if admin_email_sent:
                    success_messages.append("Admin notification email sent")
                else:
                    error_messages.append("Failed to send admin notification email")
            except Exception as e:
                logger.error(f"Error sending admin email: {str(e)}")
                error_messages.append(f"Error sending admin email: {str(e)}")
        
        # Add messages to session
        for msg in success_messages:
            messages.success(request, msg)
        for msg in error_messages:
            messages.error(request, msg)
        
        # Redirect back to order detail page
        return redirect('adminside:order_detail', order_id=order_id)
    except Exception as e:
        logger.error(f"Error sending order emails for {order_id}: {str(e)}")
        messages.error(request, f"Error sending emails: {str(e)}")
        return redirect('adminside:order_detail', order_id=order_id)

# @login_required
# @user_passes_test(is_admin)
def download_order_pdf(request, order_id):
    """
    Admin view for downloading a PDF of an order.
    """
    try:
        # In a real app, retrieve the order from the database
        # For demonstration, we'll use a mock order object
        order = {
            'order_id': order_id,
            'date': datetime.now().isoformat(),
            'status': 'Pending',
            'items': {
                'stock': [],
                'memo': [],
                'custom': []
            },
            'customer': {
                'name': 'John Doe',
                'email': 'john.doe@example.com',
                'phone': '(123) 456-7890'
            },
            'payment': {
                'subtotal': 1000.00,
                'shipping': 9.99,
                'tax': 80.00,
                'discount': 0.00,
                'total': 1089.99
            },
            'shipping_address': {
                'line1': '123 Main St',
                'line2': 'Apt 4B',
                'city': 'New York',
                'state': 'NY',
                'postal_code': '10001',
                'country': 'US'
            }
        }
        
        # Generate PDF (in a real app, this would use generate_order_pdf)
        # For demo, we'll just return a simple text response
        
        # Create HTTP response
        response = HttpResponse("This would be a PDF file", content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="Order_{order_id}.pdf"'
        
        return response
    except Exception as e:
        logger.error(f"Error generating PDF for order {order_id}: {str(e)}")
        messages.error(request, f"Error generating PDF: {str(e)}")
        return redirect('adminside:order_detail', order_id=order_id)

@login_required
@user_passes_test(is_admin)
def inventory_list(request):
    """
    Admin view for listing all inventory items with filtering and pagination.
    """
    try:
        items = Design.objects.all()
        return render(request, 'adminside/inventory.html', {'items': items})
    except Exception as e:
        logger.error(f"Error rendering admin inventory list: {str(e)}")
        messages.error(request, f"Error loading inventory: {str(e)}")
        return render(request, 'adminside/error.html', {'error': str(e)})

# @login_required
# @user_passes_test(is_admin)
def add_inventory_item(request):
    """
    Admin view for adding a new inventory item.
    """
    if request.method == 'POST':
        try:
            # Process form submission
            # In a real app, save to database
            
            messages.success(request, "Inventory item added successfully")
            return redirect('adminside:inventory')
        except Exception as e:
            logger.error(f"Error adding inventory item: {str(e)}")
            messages.error(request, f"Error adding inventory item: {str(e)}")
    
    # GET request - show the form
    return render(request, 'adminside/inventory_form.html')

# @login_required
# @user_passes_test(is_admin)
def edit_inventory_item(request, item_id):
    """
    Admin view for editing an inventory item.
    """
    if request.method == 'POST':
        try:
            # Process form submission
            # In a real app, update database
            
            messages.success(request, f"Inventory item {item_id} updated successfully")
            return redirect('adminside:inventory')
        except Exception as e:
            logger.error(f"Error updating inventory item {item_id}: {str(e)}")
            messages.error(request, f"Error updating inventory item: {str(e)}")
    
    # GET request - show the form with item data
    # In a real app, fetch item from database
    
    return render(request, 'adminside/inventory_form.html', {'item_id': item_id})

# @login_required
# @user_passes_test(is_admin)
def delete_inventory_item(request, item_id):
    """
    Admin view for deleting an inventory item.
    """
    if request.method == 'POST':
        try:
            # In a real app, delete from database
            
            messages.success(request, f"Inventory item {item_id} deleted successfully")
            return redirect('adminside:inventory')
        except Exception as e:
            logger.error(f"Error deleting inventory item {item_id}: {str(e)}")
            messages.error(request, f"Error deleting inventory item: {str(e)}")
            return redirect('adminside:inventory')
    
    # GET request - show confirmation page
    return render(request, 'adminside/confirm_delete.html', {'item_id': item_id})

@login_required
@user_passes_test(is_admin)
def toggle_inventory_status(request, item_id):
    item = get_object_or_404(Design, id=item_id)
    item.is_active = not item.is_active
    item.save()
    # Optional: log this action
    ActivityLog.objects.create(
        user=request.user,
        action='TOGGLE_INVENTORY_STATUS',
        target_model='Design',
        target_id=item.id,
        details=f"{'Activated' if item.is_active else 'Deactivated'} inventory item: {item.design_no}"
    )
    return redirect('adminside:inventory')

# Also update your customer_detail view:
@login_required
@user_passes_test(is_admin)
def customer_detail(request, customer_id):
    """
    View and manage individual customer details
    """
    customer = get_object_or_404(User, id=customer_id, is_staff=False)
    
    # Get or create customer profile
    profile, created = CustomerProfile.objects.get_or_create(user=customer)
    
    # Calculate average order value
    average_order_value = 0
    if profile.total_orders > 0:
        average_order_value = float(profile.total_spent) / profile.total_orders
    
    # Get customer orders from orders app
    try:
        from orders.models import Order
        orders = Order.objects.filter(customer=customer).order_by('-created_at')[:10]
    except:
        orders = []
    
    # Get activity logs for this customer
    activities = ActivityLog.objects.filter(
        target_model='User',
        target_id=customer.id
    ).order_by('-timestamp')[:20]
    
    context = {
        'customer': customer,
        'profile': profile,
        'orders': orders,
        'activities': activities,
        'average_order_value': average_order_value,
    }
    
    return render(request, 'adminside/customer_detail.html', context)

@login_required
@user_passes_test(is_admin)
def reports(request):
    """
    Admin view for reports dashboard.
    """
    try:
        # In a real app, fetch report data from database
        # For demo, just render the template
        
        return render(request, 'adminside/reports.html')
    except Exception as e:
        logger.error(f"Error rendering admin reports: {str(e)}")
        messages.error(request, f"Error loading reports: {str(e)}")
        return render(request, 'adminside/error.html', {'error': str(e)})

#@login_required
#@user_passes_test(is_admin)
def sales_report(request):
    """
    Admin view for sales reports.
    """
    try:
        # In a real app, fetch sales data from database
        # For demo, just render the template
        
        return render(request, 'adminside/sales_report.html')
    except Exception as e:
        logger.error(f"Error rendering admin sales report: {str(e)}")
        messages.error(request, f"Error loading sales report: {str(e)}")
        return redirect('adminside:reports')

#@login_required
#@user_passes_test(is_admin)
def inventory_report(request):
    """
    Admin view for inventory reports.
    """
    try:
        # In a real app, fetch inventory data from database
        # For demo, just render the template
        
        return render(request, 'adminside/inventory_report.html')
    except Exception as e:
        logger.error(f"Error rendering admin inventory report: {str(e)}")
        messages.error(request, f"Error loading inventory report: {str(e)}")
        return redirect('adminside:reports')

#@login_required
#@user_passes_test(is_admin)
def export_orders_csv(request):
    """
    Admin view for exporting orders as CSV.
    """
    try:
        # In a real app, fetch orders from database
        # For demo, just create a simple CSV
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="orders.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Order ID', 'Date', 'Customer', 'Items', 'Total', 'Status'])
        
        # Add sample data
        writer.writerow(['ORD12345', '2025-05-08', 'John Doe', '3 items', '$1,245.99', 'Pending'])
        writer.writerow(['ORD12344', '2025-05-07', 'Jane Smith', '3 items', '$854.50', 'In Process'])
        
        return response
    except Exception as e:
        logger.error(f"Error exporting orders to CSV: {str(e)}")
        messages.error(request, f"Error exporting orders: {str(e)}")
        return redirect('adminside:orders')

#@login_required
#@user_passes_test(is_admin)
def export_orders_pdf(request):
    """
    Admin view for exporting orders as PDF.
    """
    try:
        # In a real app, this would generate a PDF
        # For demo, just return a simple text response
        
        response = HttpResponse("This would be a PDF file with all orders", content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="orders.pdf"'
        
        return response
    except Exception as e:
        logger.error(f"Error exporting orders to PDF: {str(e)}")
        messages.error(request, f"Error exporting orders: {str(e)}")
        return redirect('adminside:orders')

#@login_required
#@user_passes_test(is_admin)
def settings(request):
    """
    Admin view for system settings.
    """
    try:
        # In a real app, fetch settings from database
        # For demo, just render the template
        
        return render(request, 'adminside/settings.html')
    except Exception as e:
        logger.error(f"Error rendering admin settings: {str(e)}")
        messages.error(request, f"Error loading settings: {str(e)}")
        return render(request, 'adminside/error.html', {'error': str(e)})

#@login_required
#@user_passes_test(is_admin)
def email_settings(request):
    """
    Admin view for email settings.
    """
    if request.method == 'POST':
        try:
            # Process form submission
            # In a real app, update email settings in database
            
            messages.success(request, "Email settings updated successfully")
            return redirect('adminside:settings')
        except Exception as e:
            logger.error(f"Error updating email settings: {str(e)}")
            messages.error(request, f"Error updating email settings: {str(e)}")
    
    # GET request - show the form
    return render(request, 'adminside/email_settings.html')


def pending_users(request):
    # List inactive customers pending approval
    pending = User.objects.filter(is_active=False)
    return render(request, 'adminside/pending_users.html', {'pending': pending})

def approve_user(request, user_id):
    user = User.objects.get(id=user_id)
    user.is_active = True
    user.save()
    # Optionally update the CustomerProfile too
    try:
        profile = CustomerProfile.objects.get(user=user)
        profile.account_status = 'active'
        profile.save()
    except CustomerProfile.DoesNotExist:
        pass
    # (Optionally: Send welcome email here)
    return redirect('pending_users')



#@login_required
#@user_passes_test(is_admin)
def users_list(request):
    """
    Admin view for listing all users with filtering and pagination.
    """
    try:
        # In a real app, fetch users from database
        # For demo, just render the template
        
        return render(request, 'adminside/users.html')
    except Exception as e:
        logger.error(f"Error rendering admin users list: {str(e)}")
        messages.error(request, f"Error loading users: {str(e)}")
        return render(request, 'adminside/error.html', {'error': str(e)})

#@login_required
#@user_passes_test(is_admin)
def add_user(request):
    """
    Admin view for adding a new user.
    """
    if request.method == 'POST':
        try:
            # Process form submission
            # In a real app, create user in database
            
            messages.success(request, "User added successfully")
            return redirect('adminside:users')
        except Exception as e:
            logger.error(f"Error adding user: {str(e)}")
            messages.error(request, f"Error adding user: {str(e)}")
    
    # GET request - show the form
    return render(request, 'adminside/user_form.html')

#@login_required
#@user_passes_test(is_admin)
def edit_user(request, user_id):
    """
    Admin view for editing a user.
    """
    if request.method == 'POST':
        try:
            # Process form submission
            # In a real app, update user in database
            
            messages.success(request, f"User #{user_id} updated successfully")
            return redirect('adminside:users')
        except Exception as e:
            logger.error(f"Error updating user {user_id}: {str(e)}")
            messages.error(request, f"Error updating user: {str(e)}")
    
    # GET request - show the form with user data
    # In a real app, fetch user from database
    
    return render(request, 'adminside/user_form.html', {'user_id': user_id})


@login_required
@user_passes_test(is_admin)
def customer_list(request):
    """
    Admin view for listing all customers with filtering, search, and bulk actions
    """
    # Get filter parameters
    status_filter = request.GET.get('status', '')
    search_query = request.GET.get('search', '')
    sort_by = request.GET.get('sort', '-date_joined')
    
    # Base queryset - exclude staff users
    customers = User.objects.filter(is_staff=False).select_related('customer_profile')
    
    # Apply status filter
    if status_filter:
        if status_filter == 'active':
            customers = customers.filter(
                is_active=True,
                customer_profile__account_status='active'
            )
        elif status_filter == 'inactive':
            customers = customers.filter(
                Q(is_active=False) | Q(customer_profile__account_status='inactive')
            )
        elif status_filter == 'suspended':
            customers = customers.filter(customer_profile__account_status='suspended')
        elif status_filter == 'pending':
            customers = customers.filter(customer_profile__account_status='pending')
    
    # Apply search
    if search_query:
        customers = customers.filter(
            Q(username__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(customer_profile__phone__icontains=search_query) |
            Q(customer_profile__company__icontains=search_query)
        )
    
    # Apply sorting
    if sort_by == 'name':
        customers = customers.order_by('first_name', 'last_name')
    elif sort_by == '-name':
        customers = customers.order_by('-first_name', '-last_name')
    elif sort_by == 'email':
        customers = customers.order_by('email')
    elif sort_by == '-email':
        customers = customers.order_by('-email')
    elif sort_by == 'date_joined':
        customers = customers.order_by('date_joined')
    elif sort_by == '-date_joined':
        customers = customers.order_by('-date_joined')
    elif sort_by == 'total_orders':
        customers = customers.order_by('customer_profile__total_orders')
    elif sort_by == '-total_orders':
        customers = customers.order_by('-customer_profile__total_orders')
    
    # Pagination
    paginator = Paginator(customers, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get summary statistics
    total_customers = User.objects.filter(is_staff=False).count()
    active_customers = User.objects.filter(
        is_staff=False,
        is_active=True,
        customer_profile__account_status='active'
    ).count()
    inactive_customers = User.objects.filter(
        is_staff=False
    ).filter(
        Q(is_active=False) | Q(customer_profile__account_status='inactive')
    ).count()
    suspended_customers = User.objects.filter(
        is_staff=False,
        customer_profile__account_status='suspended'
    ).count()
    pending_customers = User.objects.filter(
        is_staff=False,
        customer_profile__account_status='pending'
    ).count()
    
    # Calculate percentage for active customers
    active_percentage = 0
    if total_customers > 0:
        active_percentage = int((active_customers * 100) / total_customers)
    
    context = {
        'customers': page_obj,
        'total_customers': total_customers,
        'active_customers': active_customers,
        'inactive_customers': inactive_customers,
        'suspended_customers': suspended_customers,
        'pending_customers': pending_customers,
        'active_percentage': active_percentage,  # This is the key addition
        'status_filter': status_filter,
        'search_query': search_query,
        'sort_by': sort_by,
    }
    
    return render(request, 'adminside/customers.html', context)


@login_required
@user_passes_test(is_admin)
@require_POST
def toggle_customer_status(request, customer_id):
    """
    Toggle customer active/inactive status
    """
    customer = get_object_or_404(User, id=customer_id, is_staff=False)
    profile = customer.customer_profile
    
    action = request.POST.get('action')
    reason = request.POST.get('reason', '')
    
    if action == 'activate':
        # Activate customer
        customer.is_active = True
        customer.save()
        
        profile.account_status = 'active'
        profile.deactivated_at = None
        profile.deactivated_by = None
        profile.deactivation_reason = ''
        profile.save()
        
        # Log activity
        ActivityLog.objects.create(
            user=request.user,
            action='ACTIVATE',
            target_model='User',
            target_id=customer.id,
            details=f'Activated customer: {customer.email}'
        )
        
        messages.success(request, f'Customer {customer.email} has been activated.')
        
    elif action == 'deactivate':
        # Deactivate customer
        customer.is_active = False
        customer.save()
        
        profile.account_status = 'inactive'
        profile.deactivated_at = timezone.now()
        profile.deactivated_by = request.user
        profile.deactivation_reason = reason
        profile.save()
        
        # Log activity
        ActivityLog.objects.create(
            user=request.user,
            action='DEACTIVATE',
            target_model='User',
            target_id=customer.id,
            details=f'Deactivated customer: {customer.email}. Reason: {reason}'
        )
        
        messages.success(request, f'Customer {customer.email} has been deactivated.')
        
    elif action == 'suspend':
        # Suspend customer (temporary deactivation)
        customer.is_active = False
        customer.save()
        
        profile.account_status = 'suspended'
        profile.deactivated_at = timezone.now()
        profile.deactivated_by = request.user
        profile.deactivation_reason = reason
        profile.save()
        
        # Log activity
        ActivityLog.objects.create(
            user=request.user,
            action='UPDATE',
            target_model='User',
            target_id=customer.id,
            details=f'Suspended customer: {customer.email}. Reason: {reason}'
        )
        
        messages.warning(request, f'Customer {customer.email} has been suspended.')
    
    return redirect('adminside:customer_detail', customer_id=customer.id)


@login_required
@user_passes_test(is_admin)
@require_POST
def bulk_customer_action(request):
    """
    Handle bulk actions on multiple customers
    """
    action = request.POST.get('bulk_action')
    customer_ids = request.POST.getlist('customer_ids[]')
    
    if not customer_ids:
        messages.error(request, 'No customers selected.')
        return redirect('adminside:customers')
    
    customers = User.objects.filter(id__in=customer_ids, is_staff=False)
    count = customers.count()
    
    if action == 'activate':
        for customer in customers:
            customer.is_active = True
            customer.save()
            
            profile = customer.customer_profile
            profile.account_status = 'active'
            profile.deactivated_at = None
            profile.deactivated_by = None
            profile.deactivation_reason = ''
            profile.save()
        
        messages.success(request, f'{count} customers activated successfully.')
        
    elif action == 'deactivate':
        reason = request.POST.get('bulk_reason', 'Bulk deactivation')
        
        for customer in customers:
            customer.is_active = False
            customer.save()
            
            profile = customer.customer_profile
            profile.account_status = 'inactive'
            profile.deactivated_at = timezone.now()
            profile.deactivated_by = request.user
            profile.deactivation_reason = reason
            profile.save()
        
        messages.success(request, f'{count} customers deactivated successfully.')
    
    elif action == 'delete':
        # Soft delete - just mark as inactive
        for customer in customers:
            customer.is_active = False
            customer.save()
            
            profile = customer.customer_profile
            profile.account_status = 'inactive'
            profile.save()
        
        messages.warning(request, f'{count} customers marked as inactive.')
    
    # Log bulk activity
    ActivityLog.objects.create(
        user=request.user,
        action='UPDATE',
        target_model='User',
        details=f'Bulk {action} on {count} customers'
    )
    
    return redirect('adminside:customers')


@login_required
@user_passes_test(is_admin)
def customer_export(request):
    """
    Export customer data to CSV
    """
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="customers_export.csv"'
    
    writer = csv.writer(response)
    writer.writerow([
        'ID', 'Username', 'Email', 'Full Name', 'Phone', 'Company',
        'Status', 'Date Joined', 'Last Login', 'Total Orders', 'Total Spent'
    ])
    
    customers = User.objects.filter(is_staff=False).select_related('customer_profile')
    
    for customer in customers:
        profile = customer.customer_profile
        writer.writerow([
            customer.id,
            customer.username,
            customer.email,
            customer.get_full_name(),
            profile.phone if profile else '',
            profile.company if profile else '',
            profile.account_status if profile else 'active',
            customer.date_joined.strftime('%Y-%m-%d'),
            customer.last_login.strftime('%Y-%m-%d') if customer.last_login else 'Never',
            profile.total_orders if profile else 0,
            profile.total_spent if profile else 0,
        ])
    
    return response


@login_required
@user_passes_test(is_admin)
def customer_notes(request, customer_id):
    """
    Add/view notes for a customer
    """
    customer = get_object_or_404(User, id=customer_id, is_staff=False)
    
    if request.method == 'POST':
        note_text = request.POST.get('note')
        if note_text:
            ActivityLog.objects.create(
                user=request.user,
                action='UPDATE',
                target_model='User',
                target_id=customer.id,
                details=f'Note: {note_text}'
            )
            messages.success(request, 'Note added successfully.')
        
        return redirect('adminside:customer_detail', customer_id=customer.id)
    
    # This is handled in customer_detail view
    return redirect('adminside:customer_detail', customer_id=customer.id)

@staff_member_required
def password_reset_requests(request):
    requests_list = PasswordResetRequest.objects.select_related('user').order_by('-requested_at')
    return render(request, 'adminside/password_reset_requests.html', {
        'reset_requests': requests_list
    })

@staff_member_required
def approve_password_reset(request, req_id):
    reset_req = get_object_or_404(PasswordResetRequest, pk=req_id)
    if not reset_req.is_approved:
        # Approve the request
        reset_req.is_approved = True
        reset_req.processed_at = timezone.now()
        # Send password reset email
        form = PasswordResetForm({'email': reset_req.user.username})
        if form.is_valid():
            form.save(request=request)
            messages.success(request, f"Password reset email sent to {reset_req.user.username}.")
        else:
            messages.error(request, "Error sending password reset email.")
        reset_req.save()
    else:
        messages.info(request, "This request was already approved.")
    return redirect('adminside:password_reset_requests')


@login_required
@user_passes_test(lambda u: u.is_staff)
def design_list(request):
    """Enhanced design list view with comprehensive search and filtering"""
    try:
        designs = Design.objects.all().order_by('-id')
        
        # Universal search across multiple fields
        search_query = request.GET.get('search', '').strip()
        if search_query:
            designs = designs.filter(
                Q(design_no__icontains=search_query) |
                Q(category__icontains=search_query) |
                Q(subcategory__icontains=search_query) |
                Q(collection__icontains=search_query) |
                Q(vendor_code__icontains=search_query)
            )
        
        # Individual filters
        category = request.GET.get('category', '').strip()
        if category:
            designs = designs.filter(category__iexact=category)
        
        subcategory = request.GET.get('subcategory', '').strip()
        if subcategory:
            designs = designs.filter(subcategory__iexact=subcategory)
        
        collection = request.GET.get('collection', '').strip()
        if collection:
            designs = designs.filter(collection__iexact=collection)
        
        status = request.GET.get('status', '').strip()
        if status == 'active':
            designs = designs.filter(is_active=True)
        elif status == 'inactive':
            designs = designs.filter(is_active=False)
        
        # Get unique values for filter dropdowns
        all_designs = Design.objects.all()
        categories = all_designs.values_list('category', flat=True).distinct().order_by('category')
        subcategories = all_designs.values_list('subcategory', flat=True).distinct().order_by('subcategory')
        collections = all_designs.values_list('collection', flat=True).distinct().order_by('collection')
        
        # Remove None/empty values and filter
        categories = [cat for cat in categories if cat]
        subcategories = [sub_cat for sub_cat in subcategories if sub_cat]
        collections = [col for col in collections if col]
        
        # Count totals for display
        total_designs = designs.count()
        active_designs = designs.filter(is_active=True).count()
        
        # Pagination
        paginator = Paginator(designs, 25)  # Show 25 designs per page
        page = request.GET.get('page', 1)
        
        try:
            designs = paginator.page(page)
        except PageNotAnInteger:
            designs = paginator.page(1)
        except EmptyPage:
            designs = paginator.page(paginator.num_pages)
        
        # Log activity
        ActivityLog.objects.create(
            user=request.user,
            action='VIEW',
            target_model='Design',
            details=f'Viewed design list with {total_designs} results'
        )
        
        context = {
            'designs': designs,
            'categories': categories,
            'subcategories': subcategories,
            'collections': collections,
            'search_query': search_query,
            'total_designs': total_designs,
            'active_designs': active_designs,
            'page_title': 'Design Management',
        }
        
        return render(request, 'adminside/design_list.html', context)
        
    except Exception as e:
        logger.error(f"Error in design_list: {str(e)}")
        messages.error(request, f"Error loading designs: {str(e)}")
        return render(request, 'adminside/design_list.html', {
            'designs': [],
            'categories': [],
            'subcategories': [],
            'collections': [],
            'page_title': 'Design Management',
        })

@login_required
@user_passes_test(lambda u: u.is_staff)
@require_POST
def toggle_design(request, design_id):
    """Toggle single design active status"""
    try:
        design = get_object_or_404(Design, id=design_id)
        
        # Store old status for logging
        old_status = design.is_active
        
        # Toggle the status
        design.is_active = not design.is_active
        design.save()
        
        # Log the activity
        action_text = "activated" if design.is_active else "deactivated"
        ActivityLog.objects.create(
            user=request.user,
            action='UPDATE',
            target_model='Design',
            target_id=design.id,
            details=f'{action_text.title()} design "{design.design_no}" (was {"active" if old_status else "inactive"})'
        )
        
        messages.success(
            request, 
            f'Design "{design.design_no}" has been {action_text} successfully.'
        )
        
    except Exception as e:
        logger.error(f"Error toggling design {design_id}: {str(e)}")
        messages.error(request, f'Error updating design: {str(e)}')
    
    return redirect('adminside:design_list')

@login_required
@user_passes_test(lambda u: u.is_staff)
@require_POST
def bulk_toggle_designs(request):
    """Handle bulk activation/deactivation of designs"""
    try:
        action = request.POST.get('action')
        design_ids = request.POST.getlist('design_ids')
        
        if not design_ids:
            messages.error(request, 'No designs selected.')
            return redirect('adminside:design_list')
        
        if action not in ['activate', 'deactivate']:
            messages.error(request, 'Invalid action.')
            return redirect('adminside:design_list')
        
        # Get designs and update status
        designs = Design.objects.filter(id__in=design_ids)
        is_active = action == 'activate'
        
        # Store design numbers for logging
        design_numbers = list(designs.values_list('design_no', flat=True))
        
        updated_count = designs.update(is_active=is_active)
        
        # Log bulk activity
        action_text = "activated" if is_active else "deactivated"
        ActivityLog.objects.create(
            user=request.user,
            action='BULK_UPDATE',
            target_model='Design',
            details=f'Bulk {action_text} {updated_count} designs: {", ".join(design_numbers[:5])}{"..." if len(design_numbers) > 5 else ""}'
        )
        
        messages.success(
            request,
            f'{updated_count} design(s) have been {action_text} successfully.'
        )
        
    except Exception as e:
        logger.error(f"Error in bulk toggle designs: {str(e)}")
        messages.error(request, f'Error updating designs: {str(e)}')
    
    return redirect('adminside:design_list')

@login_required
@user_passes_test(lambda u: u.is_staff)
def design_export_csv(request):
    """Export filtered designs to CSV"""
    try:
        # Apply same filters as in design_list
        designs = Design.objects.all().order_by('design_no')
        
        # Apply filters from GET parameters
        search_query = request.GET.get('search', '').strip()
        if search_query:
            designs = designs.filter(
                Q(design_no__icontains=search_query) |
                Q(category__icontains=search_query) |
                Q(subcategory__icontains=search_query) |
                Q(collection__icontains=search_query) |
                Q(vendor_code__icontains=search_query)
            )
        
        category = request.GET.get('category', '').strip()
        if category:
            designs = designs.filter(category__iexact=category)
        
        subcategory = request.GET.get('subcategory', '').strip()
        if subcategory:
            designs = designs.filter(subcategory__iexact=subcategory)
        
        collection = request.GET.get('collection', '').strip()
        if collection:
            designs = designs.filter(collection__iexact=collection)
        
        status = request.GET.get('status', '').strip()
        if status == 'active':
            designs = designs.filter(is_active=True)
        elif status == 'inactive':
            designs = designs.filter(is_active=False)
        
        # Create CSV response
        response = HttpResponse(content_type='text/csv')
        timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
        response['Content-Disposition'] = f'attachment; filename="designs_export_{timestamp}.csv"'
        
        writer = csv.writer(response)
        
        # Write header
        writer.writerow([
            'Design No',
            'Category', 
            'Sub-Category',
            'Collection',
            'Vendor Code',
            'Status',
            'Created Date'
        ])
        
        # Write data
        for design in designs:
            writer.writerow([
                design.design_no,
                design.category or '',
                design.subcategory or '',
                design.collection or '',
                design.vendor_code or '',
                'Active' if design.is_active else 'Inactive',
                design.created_at.strftime('%Y-%m-%d') if hasattr(design, 'created_at') else ''
            ])
        
        # Log export activity
        ActivityLog.objects.create(
            user=request.user,
            action='EXPORT',
            target_model='Design',
            details=f'Exported {designs.count()} designs to CSV'
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Error exporting designs: {str(e)}")
        messages.error(request, f'Error exporting designs: {str(e)}')
        return redirect('adminside:design_list')

@login_required
@user_passes_test(lambda u: u.is_staff)
def design_detail_ajax(request, design_id):
    """AJAX endpoint for design details"""
    try:
        design = get_object_or_404(Design, id=design_id)
        
        data = {
            'id': design.id,
            'design_no': design.design_no,
            'category': design.category or '',
            'subcategory': design.subcategory or '',
            'collection': design.collection or '',
            'vendor_code': design.vendor_code or '',
            'is_active': design.is_active,
            'created_at': design.created_at.strftime('%Y-%m-%d %H:%M:%S') if hasattr(design, 'created_at') else '',
        }
        
        return JsonResponse(data)
        
    except Exception as e:
        logger.error(f"Error fetching design details for {design_id}: {str(e)}")
        return JsonResponse({'error': 'Design not found'}, status=404)