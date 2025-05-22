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

# @login_required
# @user_passes_test(is_admin)
def customers_list(request):
    """
    Admin view for listing all customers with filtering and pagination.
    """
    try:
        # In a real app, fetch customers from database
        # For demo, just render the template
        
        return render(request, 'adminside/customers.html')
    except Exception as e:
        logger.error(f"Error rendering admin customers list: {str(e)}")
        messages.error(request, f"Error loading customers: {str(e)}")
        return render(request, 'adminside/error.html', {'error': str(e)})

# @login_required
# @user_passes_test(is_admin)
def customer_detail(request, customer_id):
    """
    Admin view for viewing and managing a specific customer.
    """
    try:
        # In a real app, fetch customer details from database
        # For demo, just render the template
        
        return render(request, 'adminside/customer_detail.html', {'customer_id': customer_id})
    except Exception as e:
        logger.error(f"Error rendering admin customer detail: {str(e)}")
        messages.error(request, f"Error loading customer details: {str(e)}")
        return redirect('adminside:customers')

#@login_required
#@user_passes_test(is_admin)
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