# views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
User = get_user_model()
from orders.utils import get_next_custom_job_no
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_POST, require_GET
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Q, Count
from django.core.paginator import Paginator
from django.template.loader import render_to_string, get_template
from django.utils.html import strip_tags
from django.utils import timezone  # Add this line
from django.conf import settings
import requests
import json
import logging
import io
from datetime import datetime
import uuid
from django.core.cache import cache
from .models import Wishlist, Design, InventoryItem, Category, UserProfile
from orders.models import Order, OrderItem, Customer
from orders.utils import get_next_order_number
order_number = get_next_order_number()


# Initialize logger
logger = logging.getLogger('inventory')

# Try to import PDF generation library
try:
    from xhtml2pdf import pisa
    XHTML2PDF_INSTALLED = True
except ImportError:
    logger.warning("xhtml2pdf not installed. PDF generation will be disabled.")
    XHTML2PDF_INSTALLED = False

# ——— Configuration —————————————————————————————————————
API_STOCK_URL   = "https://admin.devjewels.com/mobileapi/api_stock.php"
API_DESIGN_URL  = "https://admin.devjewels.com/mobileapi/api_design.php"
USER_ID         = "admin@eg.com"
DISCOUNT_PERCENT = 15

# Order status constants
ORDER_STATUS_CHOICES = [
    "Pending",
    "In Process",
    "Completed",
    "Cancelled"
]

def login_view(request):
    """Authenticate and log in a user."""
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            return redirect('inventory:dashboard')
        messages.error(request, 'Invalid username or password.')
    return render(request, 'accounts/login.html')


def signup_view(request):
    """Register a new user with email + password confirmation."""
    if request.method == 'POST':
        username  = request.POST.get('username')
        email     = request.POST.get('email', '')
        pwd1      = request.POST.get('password1')
        pwd2      = request.POST.get('password2')

        if pwd1 != pwd2:
            messages.error(request, 'Passwords do not match.')
        elif User.objects.filter(username=username).exists():
            messages.error(request, 'Username already taken.')
        else:
            # Create the user and redirect to login
            User.objects.create_user(username=username, email=email, password=pwd1)
            messages.success(request, 'Account created. Please log in.')
            return redirect('login')
    return render(request, 'accounts/register.html')


def logout_view(request):
    """Log out the current user."""
    logout(request)
    return redirect('login')

def clear_products_cache():
    """Clear the products cache when designs are updated"""
    cache.delete('devjewels_products')
    logger.info("Products cache cleared")

def fetch_products():
    """
    Enhanced fetch_products with additional metadata
    """
    cached_products = cache.get('devjewels_products')
    if cached_products:
        return cached_products
    
    try:
        # Fetch stock data
        stock_resp = requests.post(API_STOCK_URL, json={'userid': USER_ID}, timeout=10)
        stock_resp.raise_for_status()
        stock_data = stock_resp.json().get('data', [])
        
        # Fetch design metadata
        design_resp = requests.post(API_DESIGN_URL, json={'userid': USER_ID}, timeout=10)
        design_resp.raise_for_status()
        design_data = design_resp.json().get('data', [])
        
        # Create design map
        api_design_map = {}
        for design in design_data:
            if isinstance(design, dict) and 'design_no' in design:
                api_design_map[design['design_no']] = design

        # Get active designs
        active_designs = set(
            Design.objects.filter(is_active=True)
            .values_list('design_no', flat=True)
        )
        
        # Update Design model with API metadata
        for design_no in active_designs:
            if design_no in api_design_map:
                api_design = api_design_map[design_no]
                Design.objects.filter(design_no=design_no).update(
                    category=api_design.get('category', ''),
                    subcategory=api_design.get('subcategory', ''),
                    description=api_design.get('description', ''),
                    # Add new fields if they exist in API
                    gender=api_design.get('gender', ''),
                    collection=api_design.get('collection', ''),
                    product_type=api_design.get('product_type', ''),
                    image_base_path=api_design.get('image_base_path', f"https://dev-jewels.s3.us-east-2.amazonaws.com/products/{design_no}")
                )
        
        # Group jobs by design
        jobs_map = {}
        for item in stock_data:
            design_no = item.get('design_no')
            if design_no not in active_designs:
                continue
                
            try:
                totamt = float(item.get('totamt', 0))
                discounted = totamt * (1 - DISCOUNT_PERCENT / 100)
                item['discounted_price'] = f"{discounted:.2f}"
            except (ValueError, TypeError):
                item['discounted_price'] = "0.00"
            jobs_map.setdefault(design_no, []).append(item)

        # Build products with enhanced metadata
        products = []
        designs = Design.objects.filter(is_active=True)
        
        for design in designs:
            design_no = design.design_no
            jobs = jobs_map.get(design_no, [])
            in_stock = [j for j in jobs if j.get('memostock') == '0']
            memo_only = [j for j in jobs if j.get('memostock') == '1']
            
            # Get metadata from API or database
            if design_no in api_design_map:
                api_design = api_design_map[design_no]
                metadata = {
                    'category': api_design.get('category', design.category or 'Unknown'),
                    'subcategory': api_design.get('subcategory', design.subcategory or ''),
                    'description': api_design.get('description', design.description or ''),
                    'gender': api_design.get('gender', getattr(design, 'gender', '')),
                    'collection': api_design.get('collection', getattr(design, 'collection', '')),
                    'product_type': api_design.get('product_type', getattr(design, 'product_type', '')),
                    'image_base_path': api_design.get('image_base_path', design.image_base_path)
                }
            else:
                metadata = {
                    'category': design.category or 'Unknown',
                    'subcategory': design.subcategory or '',
                    'description': design.description or '',
                    'gender': getattr(design, 'gender', ''),
                    'collection': getattr(design, 'collection', ''),
                    'product_type': getattr(design, 'product_type', ''),
                    'image_base_path': design.image_base_path
                }
            
            products.append({
                'design_no': design_no,
                **metadata,
                'jobs': jobs,
                'in_stock_jobs': in_stock,
                'memo_jobs': memo_only,
                'pcs': len(in_stock),
                'status': 'In Stock' if in_stock else 'Not In Stock',
                'created_at': design.created_at.isoformat() if hasattr(design, 'created_at') else ''
            })
        
        # Cache products
        cache.set('devjewels_products', products, 900)
        return products
        
    except Exception as e:
        logger.error(f"Error fetching products: {str(e)}", exc_info=True)
        return []

@require_GET
def get_filter_options(request):
    """
    API endpoint to get all available filter options directly from database
    """
    try:
        # Get unique categories
        categories = Design.objects.filter(is_active=True).values_list(
            'category', flat=True).distinct().order_by('category')
        
        # Get unique subcategories
        subcategories = Design.objects.filter(is_active=True).values_list(
            'subcategory', flat=True).distinct().order_by('subcategory')
        
        # Get unique genders - check if gender field exists
        genders = []
        if hasattr(Design, 'gender'):
            genders = Design.objects.filter(is_active=True).exclude(gender='').values_list(
                'gender', flat=True).distinct().order_by('gender')
        
        # Get unique collections - check if collection field exists
        collections = []
        if hasattr(Design, 'collection'):
            collections = Design.objects.filter(is_active=True).exclude(collection='').values_list(
                'collection', flat=True).distinct().order_by('collection')
        
        # Get unique product types - check if product_type field exists
        product_types = []
        if hasattr(Design, 'product_type'):
            product_types = Design.objects.filter(is_active=True).exclude(product_type='').values_list(
                'product_type', flat=True).distinct().order_by('product_type')
        
        # Filter out empty values and convert to lists
        filter_options = {
            'categories': [c for c in categories if c],
            'subcategories': [s for s in subcategories if s],
            'genders': [g for g in genders if g],
            'collections': [c for c in collections if c],
            'product_types': [p for p in product_types if p]
        }
        
        return JsonResponse({
            'success': True,
            'filters': filter_options
        })
        
    except Exception as e:
        logger.error(f"Error getting filter options: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)
    
def inventory_dashboard(request):
    """
    Renders the main dashboard (dashboard.html),
    showing only active designs.
    """
    try:
        products = fetch_products()
        
        # Products are already filtered by active designs in fetch_products()
        return render(request, 'inventory/dashboard.html', {
            'products': products
        })
    except Exception as e:
        logger.error(f"Error rendering dashboard: {str(e)}")
        return render(request, 'inventory/error.html', {
            'error': str(e)
        })
             
# application/vnd.ant.code language="python"
# application/vnd.ant.code language="python"
@require_GET
def inventory_list_ajax(request):
    """
    AJAX endpoint for loading products with advanced filters
    including job number search capability
    """
    try:
        # Parse query parameters
        page = int(request.GET.get('page', 1))
        limit = int(request.GET.get('limit', 20))
        search_query = request.GET.get('search', '').strip()
        
        # Basic filters
        category_filter = request.GET.get('category', 'all')
        status_filter = request.GET.get('status', 'instock')
        
        # Advanced filters
        gender_filter = request.GET.get('gender', 'all')
        collection_filter = request.GET.get('collection', 'all')
        subcategory_filter = request.GET.get('subcategory', 'all')
        product_type_filter = request.GET.get('producttype', 'all')
        
        # Get all products from cache/API
        all_products = fetch_products()
        
        # Log the search query for debugging
        if search_query:
            logger.info(f"Searching for: '{search_query}'")
            
        # First check if the search query exactly matches any job number
        # This is a more direct approach to find job numbers
        if search_query:
            # Check if search query could be a job number
            job_matches = []
            for product in all_products:
                # Check in stock jobs
                for job in product.get('in_stock_jobs', []):
                    if search_query.lower() in job.get('job_no', '').lower():
                        # If job matches, add this product to results
                        job_matches.append(product)
                        break  # No need to check other jobs
                        
                # If already matched, continue to next product
                if job_matches and job_matches[-1] == product:
                    continue
                    
                # Check memo jobs
                for job in product.get('memo_jobs', []):
                    if search_query.lower() in job.get('job_no', '').lower():
                        # If job matches, add this product to results
                        job_matches.append(product)
                        break  # No need to check other jobs
                        
            # If job matches found, use those results
            if job_matches:
                logger.info(f"Found {len(job_matches)} product(s) with matching job numbers")
                filtered_products = job_matches
            else:
                # If no job matches, proceed with regular search
                search_terms = search_query.lower().split()
                filtered_products = []
                
                for product in all_products:
                    # Check if any search term matches the design number or category
                    matches = True
                    design_no = product.get('design_no', '').lower()
                    category = product.get('category', '').lower()
                    subcategory = product.get('subcategory', '').lower()
                    
                    # Check if all terms match anywhere in the product data
                    for term in search_terms:
                        term_matches = (
                            term in design_no or
                            term in category or
                            term in subcategory
                        )
                        
                        if not term_matches:
                            matches = False
                            break
                    
                    if matches:
                        filtered_products.append(product)
        else:
            # If no search query, use all products
            filtered_products = all_products.copy()
            
        # Apply category filter
        if category_filter != 'all':
            filtered_products = [p for p in filtered_products if p.get('category', '').lower() == category_filter.lower()]
        
        # Apply gender filter
        if gender_filter != 'all':
            filtered_products = [p for p in filtered_products if p.get('gender', '').lower() == gender_filter.lower()]
        
        # Apply collection filter
        if collection_filter != 'all':
            filtered_products = [p for p in filtered_products if p.get('collection', '').lower() == collection_filter.lower()]
        
        # Apply subcategory filter
        if subcategory_filter != 'all':
            filtered_products = [p for p in filtered_products if p.get('subcategory', '').lower() == subcategory_filter.lower()]
        
        # Apply product type filter
        if product_type_filter != 'all':
            filtered_products = [p for p in filtered_products if p.get('product_type', '').lower() == product_type_filter.lower()]
        
        # Apply status filter
        if status_filter == 'instock':
            filtered_products = [p for p in filtered_products if p.get('in_stock_jobs')]
        elif status_filter == 'notinstock':
            filtered_products = [p for p in filtered_products if not p.get('in_stock_jobs')]
        
        # Sort the results
        sort_by = request.GET.get('sort', 'design_no')
        if sort_by == 'design_no':
            filtered_products.sort(key=lambda p: p.get('design_no', ''))
        elif sort_by == 'category':
            filtered_products.sort(key=lambda p: p.get('category', ''))
        elif sort_by == 'newest':
            filtered_products.sort(key=lambda p: p.get('created_at', ''), reverse=True)
        
        # Paginate the results
        total_count = len(filtered_products)
        start_idx = (page - 1) * limit
        end_idx = min(start_idx + limit, total_count)
        paginated_products = filtered_products[start_idx:end_idx]
        
        logger.info(f"Search found {total_count} products, returning page {page} with {len(paginated_products)} products")
        
        return JsonResponse({
            'success': True,
            'products': paginated_products,
            'has_more': end_idx < total_count,
            'total_count': total_count,
            'current_page': page
        })
        
    except Exception as e:
        logger.error(f"Error in inventory_list_ajax: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

def inventory_list(request):
    """
    Renders the inventory listing page with optimized initial data load
    """
    try:
        # Get initial active designs
        designs = Design.objects.filter(is_active=True).order_by('design_no')[:20]
        design_nos = [d.design_no for d in designs]
        
        # Get all products
        all_products = fetch_products()
        
        # Filter to only show active designs for the initial page
        filtered_products = [p for p in all_products if p.get('design_no') in design_nos]
        
        # By default, show only in-stock items on first load
        filtered_products = [p for p in filtered_products if p.get('in_stock_jobs')]
        
        # Calculate if there are more products to load
        total_count = Design.objects.filter(is_active=True).count()
        has_more = len(designs) < total_count
        
        logger.info(f"Initial products: {len(filtered_products)}, has_more: {has_more}")
        
        return render(request, 'inventory/inventory.html', {
            'products': filtered_products,
            'has_more': has_more,
            'total_count': total_count
        })
    except Exception as e:
        logger.error(f"Error rendering inventory: {str(e)}", exc_info=True)
        return render(request, 'inventory/error.html', {
            'error': str(e)
        })

def cart_view(request):
    """
    Renders the unified cart view that includes stock items, 
    memo requests, and custom orders.
    """
    try:
        # We only need products data for reference in the cart
        products = fetch_products()
        
        # Create a map of job_no -> product info for easier lookup
        inventory_data = {}
        for product in products:
            for job in product.get('in_stock_jobs', []):
                inventory_data[job.get('job_no')] = {
                    'design_no': product.get('design_no'),
                    'category': product.get('category'),
                    'available': True,
                    'price': job.get('discounted_price')
                }
            for job in product.get('memo_jobs', []):
                inventory_data[job.get('job_no')] = {
                    'design_no': product.get('design_no'),
                    'category': product.get('category'),
                    'available': False,
                    'price': job.get('discounted_price')
                }
                
        return render(request, 'inventory/cart.html', {
            'inventory_data': json.dumps(inventory_data)
        })
    except Exception as e:
        logger.error(f"Error rendering cart: {str(e)}")
        return render(request, 'inventory/error.html', {
            'error': str(e)
        })


@login_required
def wishlist_view(request):
    items = Wishlist.objects.filter(user=request.user).order_by('-added_at')
    if request.GET.get('format') == 'json':
        return JsonResponse({'items': [
            {'id': i.id, 'design_no': i.design_no, 'added_at': i.added_at.isoformat()}
            for i in items
        ]})
    return render(request, 'inventory/wishlist.html', {'items': items})

@login_required
def add_to_wishlist(request, design_no):
    # avoid duplicates
    Wishlist.objects.get_or_create(user=request.user, design_no=design_no)
    return redirect('inventory:wishlist')

@login_required
def remove_from_wishlist(request, item_id):
    item = get_object_or_404(Wishlist, id=item_id, user=request.user)
    item.delete()
    return redirect('inventory:wishlist')

@login_required
def toggle_wishlist(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST allowed'}, status=405)

    data = json.loads(request.body)
    design_no = data.get('design_no')
    if not design_no:
        return JsonResponse({'error': 'Missing design_no'}, status=400)

    # Try to create; if it already exists, delete it instead
    obj, created = Wishlist.objects.get_or_create(
        user=request.user,
        design_no=design_no
    )
    if not created:
        obj.delete()
        action = 'removed'
    else:
        action = 'added'

    # Return the new total count and what we did
    count = Wishlist.objects.filter(user=request.user).count()
    return JsonResponse({'action': action, 'count': count})


def order_view(request):
    """
    Renders the orders page that displays past orders.
    """
    try:
        return render(request, 'inventory/orders.html')
    except Exception as e:
        logger.error(f"Error rendering orders page: {str(e)}")
        return render(request, 'inventory/error.html', {'error': str(e)})


def get_stock_by_job(request, job_no):
    """
    API endpoint to fetch stock details for a specific job number.
    """
    try:
        # Re-use your existing fetch_products function 
        products = fetch_products()
        
        # Search for the job in all products
        for product in products:
            # Search in stock jobs
            for job in product.get('in_stock_jobs', []):
                if job.get('job_no') == job_no:
                    job['memostock'] = '0'  # Mark as in-stock
                    return JsonResponse(job)
            
            # Search in memo jobs
            for job in product.get('memo_jobs', []):
                if job.get('job_no') == job_no:
                    job['memostock'] = '1'  # Mark as on-memo
                    return JsonResponse(job)
                    
        # If job not found, return empty with unknown status
        return JsonResponse({
            'job_no': job_no,
            'memostock': 'unknown',
            'metal_type': 'N/A',
            'metal_quality': '',
            'metal_color': '',
            'diamond_quality': '',
            'diamond_color': '',
            'gwt': 'N/A',
            'size': 'N/A'
        })
        
    except Exception as e:
        # Log the error and return a graceful error response
        logger.error(f"Error fetching stock for job {job_no}: {str(e)}")
        return JsonResponse({
            'error': 'Failed to fetch stock information',
            'job_no': job_no,
            'memostock': 'unknown'
        }, status=500)


def get_stock_by_design(request, design_no):
    """
    API endpoint to fetch all stock details for a specific design number.
    """
    try:
        # Re-use your existing fetch_products function 
        products = fetch_products()
        
        # Find the product matching the design number
        for product in products:
            if product.get('design_no') == design_no:
                # Return the product data in the format expected by the frontend
                # Using camelCase for consistent property naming
                return JsonResponse({
                    'design_no': design_no,
                    'category': product.get('category', ''),
                    'inStockJobs': product.get('in_stock_jobs', []),  # Convert from snake_case to camelCase
                    'memoJobs': product.get('memo_jobs', []),         # Convert from snake_case to camelCase
                    'status': product.get('status', ''),
                    'pcs': product.get('pcs', 0)
                })
                
        # If design not found, return empty structure
        return JsonResponse({
            'design_no': design_no,
            'category': '',
            'inStockJobs': [],
            'memoJobs': [],
            'status': 'Not In Stock',
            'pcs': 0
        })
        
    except Exception as e:
        # Log the error and return a graceful error response
        logger.error(f"Error fetching stock for design {design_no}: {str(e)}")
        return JsonResponse({
            'error': 'Failed to fetch stock information',
            'design_no': design_no,
            'inStockJobs': [],
            'memoJobs': []
        }, status=500)

@require_POST
def create_order(request):
    try:
        data = json.loads(request.body)
        user = request.user if request.user.is_authenticated else None

        # -- 1. CUSTOMER LOGIC --
        customer_info = data.get('customer', {})
        customer = None
        
        # Get or create Customer object for record keeping
        if user:
            customer = Customer.objects.filter(user=user).first()
        if not customer and customer_info.get('email'):
            customer = Customer.objects.filter(email=customer_info.get('email')).first()
        if not customer:
            customer = Customer.objects.create(
                user=user if user else None,
                name=customer_info.get('name', ''),
                email=customer_info.get('email', ''),
                phone=customer_info.get('phone', ''),
                address_line1=customer_info.get('address_line1', ''),
                address_line2=customer_info.get('address_line2', ''),
                city=customer_info.get('city', ''),
                state=customer_info.get('state', ''),
                country=customer_info.get('country', 'USA'),
                postal_code=customer_info.get('postal_code', ''),
            )

        shipping_address = data.get('shipping_address', {})
        payment_data = data.get('payment', {})
        order_notes = data.get('notes', '')

        # -- IMPORTANT: ALWAYS generate order number server-side --
        from orders.utils import get_next_order_number
        order_number = get_next_order_number()
        
        # Log the generated order number
        logger.info(f"Generated order number: {order_number}")

        # -- 2. CREATE THE ORDER --
        shipping_line1 = shipping_address.get('line1', '') or customer.address_line1 or ''
        shipping_line2 = shipping_address.get('line2', '') or customer.address_line2 or ''
        shipping_city = shipping_address.get('city', '') or customer.city or ''
        shipping_state = shipping_address.get('state', '') or customer.state or ''
        shipping_postal = shipping_address.get('postal_code', '') or customer.postal_code or ''
        shipping_country = shipping_address.get('country', '') or customer.country or 'USA'
        
        order = Order.objects.create(
            order_number=order_number,
            order_id=order_number,  # Keep both fields synchronized
            customer=user,  # Use user instead of customer object
            customer_name=customer.name,
            customer_email=customer.email,
            customer_phone=customer.phone,
            shipping_name=shipping_address.get('name', '') or customer.name,
            shipping_email=shipping_address.get('email', '') or customer.email,
            shipping_phone=shipping_address.get('phone', '') or customer.phone,
            shipping_address_line1=shipping_line1,
            shipping_address_line2=shipping_line2,
            shipping_city=shipping_city,
            shipping_state=shipping_state,
            shipping_country=shipping_country,
            shipping_postal_code=shipping_postal,
            status='pending',
            payment_status='pending',
            payment_method=payment_data.get('method', 'standard'),
            subtotal=payment_data.get('subtotal', 0),
            tax_amount=payment_data.get('tax', 0),
            shipping_cost=payment_data.get('shipping', 0),
            shipping_amount=payment_data.get('shipping', 0),
            discount_amount=payment_data.get('discount', 0),
            total_amount=payment_data.get('total', 0),
            notes=order_notes,
            customer_notes=order_notes,
            admin_notes='',
            internal_notes='',
            tracking_number='',
            created_by=user,
        )

        # -- 3. ORDER ITEMS with complete field mapping --
        for section in ['stock', 'memo', 'custom']:
            for item in data.get('order_items', {}).get(section, []):
                # Prepare common fields
                order_item_data = {
                    'order': order,
                    'product_id': 0,  # Default value as required by DB
                    'product_name': item.get('design_no', ''),
                    'product_sku': item.get('job_no', ''),
                    'design_no': item.get('design_no', ''),
                    'job_no': item.get('job_no', ''),
                    'item_type': section,
                    'item_status': 'pending',
                    'status_updated_at': timezone.now(),
                    'quantity': 1,  # Default quantity
                    'unit_price': 0,  # Default price
                    'discount_amount': 0,
                    'total': 0,
                    # Required string fields with defaults
                    'metal_type': '',
                    'metal_quality': '',
                    'metal_color': '',
                    'diamond_quality': '',
                    'diamond_color': '',
                    'size': '',
                    'custom_remarks': '',
                }
                
                # Update fields based on item type
                if section == 'stock':
                    # Stock items have complete information
                    order_item_data.update({
                        'metal_type': item.get('metal_type', ''),
                        'metal_quality': item.get('metal_quality', ''),
                        'metal_color': item.get('metal_color', ''),
                        'diamond_quality': item.get('diamond_quality', ''),
                        'diamond_color': item.get('diamond_color', ''),
                        'size': item.get('size', ''),
                        'unit_price': float(item.get('price', 0)),
                        'gwt': float(item.get('gwt')) if item.get('gwt') else None,
                        'dwt': float(item.get('dwt')) if item.get('dwt') else None,
                    })
                
                elif section == 'memo':
                    # Memo items
                    order_item_data.update({
                        'metal_type': item.get('metal_type', ''),
                        'metal_quality': item.get('metal_quality', ''),
                        'metal_color': item.get('metal_color', ''),
                        'diamond_quality': item.get('diamond_quality', ''),
                        'diamond_color': item.get('diamond_color', ''),
                        'size': item.get('size', ''),
                        'unit_price': 0,  # Price pending for memo items
                        'memo_requested_at': item.get('requested_at', timezone.now()),
                        'gwt': float(item.get('gwt')) if item.get('gwt') else None,
                        'dwt': float(item.get('dwt')) if item.get('dwt') else None,
                    })
                
                elif section == 'custom':
                    # Assign a global unique job number to custom orders
                    order_item_data['job_no'] = get_next_custom_job_no()
                    order_item_data.update({
                        'metal_type': item.get('metal_type', ''),
                        'metal_quality': item.get('metal_quality', ''),
                        'metal_color': item.get('metal_color', ''),
                        'diamond_quality': item.get('diamond_quality', ''),
                        'diamond_color': item.get('diamond_color', ''),
                        'size': item.get('size', ''),
                        'quantity': int(item.get('qty', 1)),
                        'unit_price': 0,
                        'custom_remarks': item.get('remarks', ''),
                    })

                
                # Calculate total
                unit_price = float(order_item_data['unit_price'])
                quantity = int(order_item_data['quantity'])
                discount = float(order_item_data['discount_amount'])
                order_item_data['total'] = (unit_price * quantity) - discount
                
                # Create the order item
                OrderItem.objects.create(**order_item_data)

        logger.info(f"Order {order.order_number} created successfully with items")
        
        # Send confirmation emails if configured
        try:
            # Prepare order data for emails
            order_data = {
                'order_id': order.order_number,
                'date': order.created_at.isoformat(),
                'status': order.status,
                'customer': {
                    'name': customer.name,
                    'email': customer.email,
                    'phone': customer.phone,
                },
                'shipping_address': {
                    'line1': shipping_line1,
                    'line2': shipping_line2,
                    'city': shipping_city,
                    'state': shipping_state,
                    'postal_code': shipping_postal,
                    'country': shipping_country,
                },
                'payment': {
                    'subtotal': float(order.subtotal),
                    'shipping': float(order.shipping_cost),
                    'tax': float(order.tax_amount),
                    'discount': float(order.discount_amount),
                    'total': float(order.total_amount),
                    'method': order.payment_method,
                },
                'items': data.get('order_items', {}),
            }
            
            # Send customer email
            if customer.email:
                send_order_confirmation_email(order_data, customer.email)
            
            # Send admin notification
            send_admin_order_notification(order_data)
        except Exception as email_error:
            logger.error(f"Error sending order emails: {str(email_error)}")
            # Don't fail the order creation if email sending fails

        return JsonResponse({
            'success': True,
            'order_id': order.order_number,
            'message': 'Order created and saved successfully'
        })

    except Exception as e:
        logger.error(f"Error creating order: {str(e)}", exc_info=True)
        return JsonResponse({'success': False, 'error': str(e)}, status=500)
    
    
@login_required
def my_orders_api(request):
    """Return orders for the current logged-in customer as JSON."""
    user = request.user
    
    try:
        # Since Order.customer points to User model, filter directly
        orders = Order.objects.filter(customer=user).order_by('-created_at')
        
        # Also check for orders created by this user
        # (in case some orders were created without customer field)
        if not orders.exists():
            orders = Order.objects.filter(created_by=user).order_by('-created_at')
        
        # Process orders
        order_list = []
        for order in orders:
            items = order.items.all()
            
            # Group items by type for display
            order_items = {
                'stock': [],
                'memo': [],
                'custom': []
            }
            
            for item in items:
                serialized = {
                    "item_type": item.item_type,
                    "item_status": item.item_status,
                    "design_no": item.design_no,
                    "job_no": item.job_no,
                    "order_id": order.order_id,
                    "quantity": item.quantity,
                    "unit_price": float(item.unit_price) if item.unit_price else 0.0,
                    "total": float(item.total) if item.total else 0.0,
                    "metal_type": item.metal_type,
                    "metal_quality": item.metal_quality,
                    "metal_color": item.metal_color,
                    "diamond_quality": item.diamond_quality,
                    "diamond_color": item.diamond_color,
                    "size": item.size,
                }
                
                # Add to appropriate category
                if item.item_type in order_items:
                    order_items[item.item_type].append(serialized)
            
            order_list.append({
                "order_id": order.order_id,
                "date": order.created_at.isoformat(),
                "status": order.status.title() if order.status else "Pending",
                "items": order_items,
                "total_items": len(items),
            })
        
        return JsonResponse({
            'success': True, 
            'orders': order_list,
            'total_orders': len(order_list)
        })
        
    except Exception as e:
        print(f"Error fetching orders: {e}")
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'success': False,
            'error': 'Failed to fetch orders',
            'orders': []
        }, status=500)

@csrf_exempt
@require_POST
def update_order_status(request, order_id):
    """
    API endpoint to update an order's status.
    
    Expected JSON format:
    {
        "status": "In Process" // one of: Pending, In Process, Completed, Cancelled
    }
    """
    try:
        # Parse request body
        data = json.loads(request.body)
        
        # Validate required fields
        if 'status' not in data:
            return JsonResponse({
                'success': False,
                'error': 'Missing required field: status'
            }, status=400)
            
        new_status = data['status']
        
        # Validate status value
        if new_status not in ORDER_STATUS_CHOICES:
            valid_statuses = ", ".join(ORDER_STATUS_CHOICES)
            return JsonResponse({
                'success': False,
                'error': f'Invalid status value. Must be one of: {valid_statuses}'
            }, status=400)
        
        # In a real application, update the database here
        # For this example, we'll just log it
        logger.info(f"Updated order {order_id} status to {new_status}")
        
        return JsonResponse({
            'success': True,
            'order_id': order_id,
            'status': new_status,
            'message': 'Order status updated successfully'
        })
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON in request body'
        }, status=400)
    except Exception as e:
        logger.error(f"Error updating order status: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@require_GET
def search_inventory(request):
    """
    API endpoint to search inventory with improved filters and pagination.
    
    Query Parameters:
    - query: Search term for design_no, category, etc.
    - category: Filter by category
    - status: Filter by status (In Stock, Not In Stock)
    - page: Page number (default: 1)
    - limit: Results per page (default: 20, max: 100)
    - sort: Sort field (default: design_no)
    - sort_dir: Sort direction (asc or desc, default: asc)
    """
    try:
        # Get query parameters
        query = request.GET.get('query', '').lower()
        category = request.GET.get('category', '').lower()
        status = request.GET.get('status', '').lower()
        page = max(1, int(request.GET.get('page', 1)))
        limit = min(100, max(1, int(request.GET.get('limit', 20))))
        sort_field = request.GET.get('sort', 'design_no')
        sort_dir = request.GET.get('sort_dir', 'asc')
        
        # Fetch all products
        products = fetch_products()
        
        # Apply filters
        filtered_products = []
        for product in products:
            # Skip if doesn't match category filter
            if category and category not in product.get('category', '').lower():
                continue
                
            # Skip if doesn't match status filter
            if status and status != product.get('status', '').lower().replace(' ', ''):
                continue
                
            # Skip if doesn't match search query
            if query:
                design_no = product.get('design_no', '').lower()
                product_category = product.get('category', '').lower()
                
                # Check if query matches any field
                if query not in design_no and query not in product_category:
                    # Also check jobs
                    found_in_jobs = False
                    for job in product.get('jobs', []):
                        job_no = job.get('job_no', '').lower()
                        if query in job_no:
                            found_in_jobs = True
                            break
                            
                    if not found_in_jobs:
                        continue
            
            # If we get here, the product matches all filters
            filtered_products.append(product)
        
        # Sort results
        reverse_sort = sort_dir.lower() == 'desc'
        
        if sort_field == 'design_no':
            filtered_products.sort(key=lambda p: p.get('design_no', ''), reverse=reverse_sort)
        elif sort_field == 'category':
            filtered_products.sort(key=lambda p: p.get('category', ''), reverse=reverse_sort)
        elif sort_field == 'pcs':
            filtered_products.sort(key=lambda p: p.get('pcs', 0), reverse=reverse_sort)
        
        # Calculate pagination
        total_results = len(filtered_products)
        total_pages = (total_results + limit - 1) // limit  # Ceiling division
        
        # Slice results for requested page
        start_idx = (page - 1) * limit
        end_idx = min(start_idx + limit, total_results)
        paginated_results = filtered_products[start_idx:end_idx]
        
        # Return paginated results
        return JsonResponse({
            'success': True,
            'results': paginated_results,
            'pagination': {
                'page': page,
                'limit': limit,
                'total_results': total_results,
                'total_pages': total_pages
            }
        })
    except Exception as e:
        logger.error(f"Error searching inventory: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)
        
@require_GET
def get_order_details(request, order_id):
    """
    API endpoint to fetch details of a specific order.
    
    This is used by the orders page to display order details.
    In a real application, this would query the database.
    For this prototype, we'll return a simple response with mock data.
    
    Returns:
        JsonResponse: Order details including items and status
    """
    try:
        # In a real application, you would query the database
        # For this example, return a mock successful response
        logger.info(f"Fetching details for order {order_id}")
        
        return JsonResponse({
            'success': True,
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
            'shipping_address': {
                'line1': '123 Main St',
                'line2': 'Apt 4B',
                'city': 'New York',
                'state': 'NY',
                'postal_code': '10001',
                'country': 'US'
            },
            'payment': {
                'subtotal': 1000.00,
                'shipping': 9.99,
                'tax': 80.00,
                'discount': 0.00,
                'total': 1089.99,
                'method': 'Credit Card'
            }
        })
    except Exception as e:
        logger.error(f"Error fetching order details for {order_id}: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@csrf_exempt
@require_POST
def add_to_cart(request):
    """
    API endpoint to add items to cart.
    
    Expected JSON format:
    {
        "item_type": "stock|memo|custom",
        "item_data": {...}
    }
    
    For localStorage-based implementation, this just validates the data
    and returns success. In a real application, this would add to a 
    server-side cart.
    
    Returns:
        JsonResponse: Success status and cart item count
    """
    try:
        # Parse request body
        data = json.loads(request.body)
        
        # Validate required fields
        if 'item_type' not in data:
            return JsonResponse({
                'success': False,
                'error': 'Missing required field: item_type'
            }, status=400)
            
        if 'item_data' not in data:
            return JsonResponse({
                'success': False,
                'error': 'Missing required field: item_data'
            }, status=400)
            
        item_type = data['item_type']
        
        # Validate item type
        valid_types = ['stock', 'memo', 'custom']
        if item_type not in valid_types:
            return JsonResponse({
                'success': False,
                'error': f'Invalid item_type. Must be one of: {", ".join(valid_types)}'
            }, status=400)
            
        # In a real application, add to database
        # For localStorage-based implementation, just return success
        logger.info(f"Added item of type {item_type} to cart")
        
        return JsonResponse({
            'success': True,
            'message': 'Item added to cart successfully',
            'item_type': item_type
        })
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON in request body'
        }, status=400)
    except Exception as e:
        logger.error(f"Error adding item to cart: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@csrf_exempt
@require_POST
def remove_from_cart(request):
    """
    API endpoint to remove items from cart.
    
    Expected JSON format:
    {
        "item_type": "stock|memo|custom",
        "item_id": "..."
    }
    
    For localStorage-based implementation, this just validates the data
    and returns success. In a real application, this would remove from 
    a server-side cart.
    
    Returns:
        JsonResponse: Success status
    """
    try:
        # Parse request body
        data = json.loads(request.body)
        
        # Validate required fields
        if 'item_type' not in data:
            return JsonResponse({
                'success': False,
                'error': 'Missing required field: item_type'
            }, status=400)
            
        if 'item_id' not in data:
            return JsonResponse({
                'success': False,
                'error': 'Missing required field: item_id'
            }, status=400)
            
        item_type = data['item_type']
        item_id = data['item_id']
        
        # Validate item type
        valid_types = ['stock', 'memo', 'custom']
        if item_type not in valid_types:
            return JsonResponse({
                'success': False,
                'error': f'Invalid item_type. Must be one of: {", ".join(valid_types)}'
            }, status=400)
            
        # In a real application, remove from database
        # For localStorage-based implementation, just return success
        logger.info(f"Removed item of type {item_type} with ID {item_id} from cart")
        
        return JsonResponse({
            'success': True,
            'message': 'Item removed from cart successfully'
        })
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON in request body'
        }, status=400)
    except Exception as e:
        logger.error(f"Error removing item from cart: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@login_required
def admin_orders_view(request):
    """
    Admin view for managing all orders.
    
    This page allows admins to view and manage all orders, 
    including updating status, viewing details, etc.
    
    Returns:
        HttpResponse: Rendered admin orders page
    """
    try:
        # In a real application, you would query the database
        # For this prototype, just render the template
        return render(request, 'admin/orders.html')
    except Exception as e:
        logger.error(f"Error rendering admin orders page: {str(e)}")
        return render(request, 'inventory/error.html', {
            'error': str(e)
        })

@login_required
@require_POST
def admin_update_order(request, order_id):
    """
    Admin endpoint for updating order status and details.
    
    Expected POST data:
    - status: New order status
    - notes: Admin notes about the order
    
    Returns:
        HttpResponse: Redirect to admin orders page
    """
    try:
        new_status = request.POST.get('status')
        
        # Validate status
        if new_status not in ORDER_STATUS_CHOICES:
            messages.error(request, f"Invalid status: {new_status}")
            return redirect('admin_orders')
            
        # In a real application, update the database
        # For this prototype, just show a success message
        logger.info(f"Admin updated order {order_id} status to {new_status}")
        messages.success(request, f"Order {order_id} updated successfully")
        
        return redirect('admin_orders')
    except Exception as e:
        logger.error(f"Error updating order {order_id}: {str(e)}")
        messages.error(request, f"Error updating order: {str(e)}")
        return redirect('admin_orders')

@login_required
def admin_inventory_view(request):
    """
    Admin view for managing inventory.
    
    This page allows admins to view and manage inventory items,
    including updating stock, prices, etc.
    
    Returns:
        HttpResponse: Rendered admin inventory page
    """
    try:
        # Fetch products for the inventory view
        products = fetch_products()
        return render(request, 'admin/inventory.html', {
            'products': products
        })
    except Exception as e:
        logger.error(f"Error rendering admin inventory page: {str(e)}")
        return render(request, 'inventory/error.html', {
            'error': str(e)
        })

@require_GET
def export_orders_csv(request):
    """
    Export orders as CSV file.
    
    This endpoint generates a CSV file with order data for download.
    In a real application, this would query the database.
    
    Returns:
        HttpResponse: CSV file for download
    """
    try:
        # In a real application, query the database
        # For this prototype, return a simple CSV with headers
        
        import csv
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="orders.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Order ID', 'Date', 'Customer', 'Items', 'Total', 'Status'])
        
        # In a real application, add rows from database
        # For this prototype, just return the headers
        
        return response
    except Exception as e:
        logger.error(f"Error exporting orders to CSV: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@require_GET
def export_orders_pdf(request):
    """
    Export orders as PDF file.
    
    This endpoint generates a PDF file with order data for download.
    In a real application, this would query the database and use 
    a PDF generation library.
    
    Returns:
        HttpResponse: PDF file for download
    """
    try:
        # In a real application, this would generate a PDF
        # For this prototype, just return a message
        return JsonResponse({
            'success': False,
            'error': 'PDF export not implemented in prototype'
        }, status=501)  # 501 Not Implemented
    except Exception as e:
        logger.error(f"Error exporting orders to PDF: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

# Webhook handler for payment processing callbacks
@csrf_exempt
def payment_webhook(request):
    """
    Webhook endpoint for payment processor callbacks.
    
    This endpoint receives callback notifications from payment processors
    like Stripe, PayPal, etc. and updates order status accordingly.
    
    Returns:
        JsonResponse: Success status
    """
    try:
        # In a real application, verify signature and process webhook
        # For this prototype, just return success
        logger.info("Received payment webhook")
        return JsonResponse({
            'success': True
        })
    except Exception as e:
        logger.error(f"Error processing payment webhook: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)
        
def generate_order_pdf(order_data):
    """
    Generate a PDF file for the order.
    
    Args:
        order_data (dict): Order information including items, customer details, etc.
        
    Returns:
        BytesIO: PDF file as BytesIO object, or None if generation fails
    """
    try:
        # Check if PDF generation is available
        if not XHTML2PDF_INSTALLED:
            logger.warning("Cannot generate PDF: xhtml2pdf not installed")
            return None
            
        # Get the HTML template
        template = get_template('emails/order_pdf_template.html')
        
        # Render the template with order data
        html = template.render({'order': order_data})
        
        # Create a BytesIO buffer to receive the PDF data
        result = io.BytesIO()
        
        # Generate PDF
        pdf = pisa.pisaDocument(
            io.BytesIO(html.encode("UTF-8")), 
            result,
            encoding='UTF-8'
        )
        
        # Return the PDF file if successful
        if not pdf.err:
            # Reset buffer position to the beginning
            result.seek(0)
            return result
        else:
            logger.error(f"Error generating PDF: {pdf.err}")
            return None
    except Exception as e:
        logger.error(f"Error generating order PDF: {str(e)}")
        return None

def send_order_confirmation_email(order_data, to_email):
    """
    Send order confirmation email with PDF attachment to customer.
    
    Args:
        order_data (dict): Order information including items, customer details, etc.
        to_email (str): Recipient email address
        
    Returns:
        bool: True if email sent successfully, False otherwise
    """
    try:
        # Check if email settings are configured
        if not hasattr(settings, 'EMAIL_HOST') or not settings.EMAIL_HOST:
            logger.warning("Email settings not configured. Skipping email send.")
            return False
            
        # Email subject
        subject = f"Order Confirmation - {order_data['order_id']}"
        
        # Render HTML email content
        html_content = render_to_string(
            'emails/customer_order_confirmation.html', 
            {'order': order_data}
        )
        
        # Create plain text version
        text_content = strip_tags(html_content)
        
        # Create email
        from django.core.mail import EmailMultiAlternatives
        email = EmailMultiAlternatives(
            subject,
            text_content,
            settings.DEFAULT_FROM_EMAIL,
            [to_email]
        )
        
        # Attach HTML content
        email.attach_alternative(html_content, "text/html")
        
        # Generate and attach PDF
        pdf_file = generate_order_pdf(order_data)
        if pdf_file:
            email.attach(
                f"Order_{order_data['order_id']}.pdf",
                pdf_file.read(),
                'application/pdf'
            )
        
        # Send email
        email.send(fail_silently=False)
        logger.info(f"Order confirmation email sent to {to_email} for order {order_data['order_id']}")
        return True
    except Exception as e:
        logger.error(f"Error sending order confirmation email: {str(e)}")
        return False

def send_admin_order_notification(order_data):
    """
    Send order notification email with PDF attachment to admin.
    
    Args:
        order_data (dict): Order information including items, customer details, etc.
        
    Returns:
        bool: True if email sent successfully, False otherwise
    """
    try:
        # Check if email settings are configured
        if not hasattr(settings, 'EMAIL_HOST') or not settings.EMAIL_HOST:
            logger.warning("Email settings not configured. Skipping email send.")
            return False
            
        # Get admin email from settings
        admin_email = getattr(settings, 'ADMIN_ORDER_EMAIL', None)
        
        if not admin_email:
            logger.warning("ADMIN_ORDER_EMAIL not configured. Skipping email send.")
            return False
            
        # Email subject
        subject = f"New Order Received - {order_data['order_id']}"
        
        # Render HTML email content - using admin-specific template
        html_content = render_to_string(
            'emails/admin_order_notification.html', 
            {'order': order_data}
        )
        
        # Create plain text version
        text_content = strip_tags(html_content)
        
        # Create email
        from django.core.mail import EmailMultiAlternatives
        email = EmailMultiAlternatives(
            subject,
            text_content,
            settings.DEFAULT_FROM_EMAIL,
            [admin_email]
        )
        
        # Attach HTML content
        email.attach_alternative(html_content, "text/html")
        
        # Generate and attach PDF
        pdf_file = generate_order_pdf(order_data)
        if pdf_file:
            email.attach(
                f"Order_{order_data['order_id']}.pdf",
                pdf_file.read(),
                'application/pdf'
            )
        
        # Send email
        email.send(fail_silently=False)
        logger.info(f"Order notification email sent to admin for order {order_data['order_id']}")
        return True
    except Exception as e:
        logger.error(f"Error sending admin order notification email: {str(e)}")
        return False
    
@login_required
@require_POST
def send_order_emails(request, order_id):
    """
    Manually send or resend order confirmation emails.
    
    This endpoint is for admin use to manually send or resend emails
    for a specific order, either because the automatic emails failed
    or because changes were made to the order.
    
    Args:
        request: HTTP request
        order_id: Order ID to send emails for
    
    Returns:
        HttpResponse: Redirect to admin order detail page with status message
    """
    try:
        # In a real application, retrieve the order from the database
        # For this example, we'll use a mock order object
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
        customer_email = order['customer']['email']
        
        # Check which emails to send
        send_to_customer = request.POST.get('send_to_customer') == 'on'
        send_to_admin = request.POST.get('send_to_admin') == 'on'
        
        success_messages = []
        error_messages = []
        
        # Send customer email if requested
        if send_to_customer:
            customer_email_sent = send_order_confirmation_email(order, customer_email)
            if customer_email_sent:
                success_messages.append(f"Confirmation email sent to {customer_email}")
            else:
                error_messages.append(f"Failed to send confirmation email to {customer_email}")
        
        # Send admin email if requested
        if send_to_admin:
            admin_email_sent = send_admin_order_notification(order)
            if admin_email_sent:
                success_messages.append("Admin notification email sent")
            else:
                error_messages.append("Failed to send admin notification email")
        
        # Add messages to session
        for msg in success_messages:
            messages.success(request, msg)
        for msg in error_messages:
            messages.error(request, msg)
        
        # Redirect back to order detail page
        return redirect('admin_order_detail', order_id=order_id)
    except Exception as e:
        logger.error(f"Error sending order emails for {order_id}: {str(e)}")
        messages.error(request, f"Error sending emails: {str(e)}")
        return redirect('admin_order_detail', order_id=order_id)


# Generate and download order PDF
@login_required
def download_order_pdf(request, order_id):
    """
    Generate and download a PDF for a specific order.
    
    Args:
        request: HTTP request
        order_id: Order ID to generate PDF for
    
    Returns:
        HttpResponse: PDF file for download
    """
    try:
        # In a real application, retrieve the order from the database
        # For this example, we'll use a mock order object
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
        
        # Generate PDF
        pdf_file = generate_order_pdf(order)
        
        if not pdf_file:
            messages.error(request, "Failed to generate PDF")
            return redirect('admin_order_detail', order_id=order_id)
        
        # Create HTTP response with PDF
        response = HttpResponse(pdf_file.read(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="Order_{order_id}.pdf"'
        
        return response
    except Exception as e:
        logger.error(f"Error generating PDF for order {order_id}: {str(e)}")
        messages.error(request, f"Error generating PDF: {str(e)}")
        return redirect('admin_order_detail', order_id=order_id)
    
@login_required
@require_GET
def get_order_details_api(request, order_id):
    """
    API endpoint to fetch detailed information about a specific order.
    Returns order with all items grouped by type (stock, memo, custom).
    """
    try:
        # Get the order with related customer data
        order = Order.objects.filter(
            Q(order_id=order_id) | Q(order_number=order_id)
        ).select_related('customer').prefetch_related('items').first()
        
        if not order:
            return JsonResponse({
                'success': False,
                'error': 'Order not found'
            }, status=404)
        
        # Check if user has permission to view this order
        if request.user.is_authenticated:
            # For staff users, allow access to all orders
            if request.user.is_staff:
                pass  # Staff can view all orders
            else:
                # For regular users, check if they own the order
                can_view = False
                
                # Check if order.customer points to the user (based on your current model)
                if order.customer == request.user:
                    can_view = True
                
                # Also check if order was created by this user
                if order.created_by == request.user:
                    can_view = True
                
                # Check if there's a Customer object for this user
                if not can_view and hasattr(order, 'customer') and order.customer:
                    # If order.customer is actually a Customer model instance
                    try:
                        from orders.models import Customer
                        if isinstance(order.customer, Customer):
                            if order.customer.user == request.user:
                                can_view = True
                    except:
                        pass
                
                # Check by email as fallback
                if not can_view and order.customer_email == request.user.email:
                    can_view = True
                
                if not can_view:
                    return JsonResponse({
                        'success': False,
                        'error': 'Permission denied'
                    }, status=403)
        
        # Get all order items and group by type
        items = order.items.all()
        
        # Group items by type
        order_items = {
            'stock': [],
            'memo': [],
            'custom': []
        }
        
        for item in items:
            item_data = {
                "id": item.id,
                "item_type": item.item_type,
                "item_status": item.item_status,
                "design_no": item.design_no,
                "job_no": item.job_no,
                "product_name": item.product_name,
                "product_sku": item.product_sku,
                "quantity": item.quantity,
                "unit_price": float(item.unit_price),
                "total": float(item.total),
                "metal_type": item.metal_type,
                "metal_quality": item.metal_quality,
                "metal_color": item.metal_color,
                "diamond_quality": item.diamond_quality,
                "diamond_color": item.diamond_color,
                "size": item.size,
                "gwt": float(item.gwt) if item.gwt else None,
                "dwt": float(item.dwt) if item.dwt else None,
                "custom_remarks": item.custom_remarks,
                "created_at": item.created_at.isoformat() if item.created_at else None,
                "status_updated_at": item.status_updated_at.isoformat() if item.status_updated_at else None,
            }
            
            # Add type-specific fields
            if item.item_type == 'memo':
                item_data["memo_requested_at"] = item.memo_requested_at.isoformat() if hasattr(item, 'memo_requested_at') and item.memo_requested_at else None
                item_data["requested_at"] = item_data["memo_requested_at"] or item_data["created_at"]
            
            # Add to appropriate list
            if item.item_type in order_items:
                order_items[item.item_type].append(item_data)
        
        # Get customer data - handle both User and Customer models
        if hasattr(order.customer, 'name'):
            # order.customer is a Customer model instance
            customer_name = order.customer_name or order.customer.name or 'N/A'
            customer_email = order.customer_email or order.customer.email or 'N/A'
            customer_phone = order.customer_phone or order.customer.phone or 'N/A'
        else:
            # order.customer is a User model instance
            customer_name = order.customer_name or (order.customer.get_full_name() if order.customer else '') or 'N/A'
            customer_email = order.customer_email or (order.customer.email if order.customer else '') or 'N/A'
            customer_phone = order.customer_phone or 'N/A'
        
        # Get shipping address - prioritize order's shipping data
        shipping_line1 = order.shipping_address_line1 or ''
        shipping_line2 = order.shipping_address_line2 or ''
        shipping_city = order.shipping_city or ''
        shipping_state = order.shipping_state or ''
        shipping_postal = order.shipping_postal_code or ''
        shipping_country = order.shipping_country or 'USA'
        
        # Build response
        response_data = {
            "success": True,
            "order_id": order.order_id,
            "order_number": order.order_number,
            "status": order.status.title() if order.status else 'Pending',
            "date": order.created_at.isoformat(),
            "created_at": order.created_at.isoformat(),
            
            # Customer information
            "customer": {
                "name": customer_name,
                "email": customer_email,
                "phone": customer_phone,
            },
            "customer_name": customer_name,
            "customer_email": customer_email,
            "customer_phone": customer_phone,
            
            # Shipping address (both nested and flat structure for compatibility)
            "shipping_address": {
                "line1": shipping_line1,
                "line2": shipping_line2,
                "city": shipping_city,
                "state": shipping_state,
                "postal_code": shipping_postal,
                "country": shipping_country,
            },
            "shipping_address_line1": shipping_line1,
            "shipping_address_line2": shipping_line2,
            "shipping_city": shipping_city,
            "shipping_state": shipping_state,
            "shipping_postal_code": shipping_postal,
            "shipping_country": shipping_country,
            
            # Payment information
            "payment": {
                "subtotal": float(order.subtotal or 0),
                "shipping": float(order.shipping_cost or 0),
                "tax": float(order.tax_amount or 0),
                "discount": float(order.discount_amount or 0),
                "total": float(order.total_amount or 0),
                "method": order.payment_method or 'Standard',
                "shipping_method": "Standard",
            },
            "payment_method": order.payment_method or 'Standard',
            "payment_status": order.payment_status or 'pending',
            "subtotal": float(order.subtotal or 0),
            "shipping_cost": float(order.shipping_cost or 0),
            "shipping_amount": float(order.shipping_cost or 0),
            "tax_amount": float(order.tax_amount or 0),
            "discount_amount": float(order.discount_amount or 0),
            "total_amount": float(order.total_amount or 0),
            
            # Additional fields
            "tracking_number": order.tracking_number or '',
            "notes": order.notes or '',
            "customer_notes": order.customer_notes or '',
            "admin_notes": order.admin_notes or '',
            
            # Status timestamps
            "processed_at": order.processed_at.isoformat() if hasattr(order, 'processed_at') and order.processed_at else None,
            "shipped_date": order.shipped_date.isoformat() if hasattr(order, 'shipped_date') and order.shipped_date else None,
            "delivered_date": order.delivered_date.isoformat() if hasattr(order, 'delivered_date') and order.delivered_date else None,
            "completed_at": order.completed_at.isoformat() if hasattr(order, 'completed_at') and order.completed_at else None,
            "cancelled_at": order.cancelled_at.isoformat() if hasattr(order, 'cancelled_at') and order.cancelled_at else None,

            # Items grouped by type
            "items": order_items,
        }
        
        return JsonResponse(response_data)
        
    except Exception as e:
        logger.error(f"Error fetching order details for {order_id}: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': 'Internal server error'
        }, status=500)