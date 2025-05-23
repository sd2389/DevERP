from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_POST, require_GET
from django.core.paginator import Paginator
import json
import logging
import csv
from datetime import datetime
from inventory.models import Design
from django.contrib.auth import authenticate, login
from .decorators import admin_login_required
from django.contrib.auth.models import User
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.utils import timezone
from .models import CustomerProfile, ActivityLog

# Setup logger
logger = logging.getLogger('adminside')

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

# Define admin check function
def is_admin(user):
    """Check if the user is an admin"""
    return user.is_staff or user.is_superuser

# @login_required
# @user_passes_test(is_admin)
def dashboard(request):
    """
    Admin dashboard view showing summary statistics and recent activities.
    """
    try:
        # In a real app, you'd fetch this data from database
        # For demonstration, we're using static data

        # Render the dashboard template
        return render(request, 'adminside/dashboard.html')
    except Exception as e:
        logger.error(f"Error rendering admin dashboard: {str(e)}")
        messages.error(request, f"Error loading dashboard: {str(e)}")
        return render(request, 'adminside/error.html', {'error': str(e)})



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

# @login_required
# @user_passes_test(is_admin)
def inventory_list(request):
    """
    Admin view for listing all inventory items with filtering and pagination.
    """
    try:
        # In a real app, fetch inventory from database
        # For demo, just render the template
        
        return render(request, 'adminside/inventory.html')
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