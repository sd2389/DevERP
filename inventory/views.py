from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_GET
from django.views.decorators.csrf import csrf_exempt
import requests
import json
import logging
from .models import Design
from datetime import datetime
import uuid

# Initialize logger
logger = logging.getLogger('inventory')

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
    return render(request, 'auth/login.html')


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
    return render(request, 'auth/signup.html')


def logout_view(request):
    """Log out the current user."""
    logout(request)
    return redirect('login')


def fetch_products():
    """
    Fetch stock data from DevJewels API,
    filter by active designs in our database,
    compute discounted prices, and group jobs by design.
    """
    try:
        # 1) Fetch raw stock data
        stock_resp = requests.post(API_STOCK_URL, json={'userid': USER_ID}, timeout=10)
        stock_resp.raise_for_status()
        stock_data = stock_resp.json().get('data', [])

        # 2) Get active designs from our database
        active_designs = set(
            Design.objects.filter(is_active=True)
            .values_list('design_no', flat=True)
        )
        
        # 3) Group jobs per design and compute discounted_price
        jobs_map = {}
        for item in stock_data:
            # Skip if design is not active in our database
            design_no = item.get('design_no')
            if design_no not in active_designs:
                continue
                
            try:
                totamt = float(item.get('totamt', 0))
                # apply percent discount
                discounted = totamt * (1 - DISCOUNT_PERCENT / 100)
                item['discounted_price'] = f"{discounted:.2f}"
            except (ValueError, TypeError):
                item['discounted_price'] = "0.00"
            jobs_map.setdefault(design_no, []).append(item)

        # 4) Get design metadata from our database for all active designs
        design_metadata = {
            d.design_no: {
                'design_no': d.design_no,
                'category': d.category,
                'subcategory': d.subcategory,
                'description': d.description,
                'image_base_path': d.image_base_path
            }
            for d in Design.objects.filter(is_active=True)
        }

        # 5) Build product summaries
        # 5) Build product summaries (for all active designs!)
        products = []
        for d in Design.objects.filter(is_active=True):
            design_no = d.design_no
            jobs = jobs_map.get(design_no, [])
            in_stock = [j for j in jobs if j.get('memostock') == '0']
            memo_only = [j for j in jobs if j.get('memostock') == '1']
            products.append({
                'design_no': design_no,
                'category': getattr(d, 'category', 'Unknown'),
                'subcategory': getattr(d, 'subcategory', ''),
                'description': getattr(d, 'description', ''),
                'image_base_path': getattr(d, 'image_base_path', f"https://dev-jewels.s3.us-east-2.amazonaws.com/products/{design_no}"),
                'jobs': jobs,
                'in_stock_jobs': in_stock,
                'memo_jobs': memo_only,
                'pcs': len(in_stock),
                'status': 'In Stock' if in_stock else 'Not In Stock',
            })
                    
        logger.info(f"Successfully fetched {len(products)} products with active designs")
        return products
    except Exception as e:
        logger.error(f"Error fetching products: {str(e)}")
        # Return empty list in case of error
    return []


def inventory_dashboard(request):
    """
    Renders the main dashboard (dashboard.html),
    showing only active designs.
    """
    try:
        products = fetch_products()

        # → Only keep products whose design_no is marked active
        active_nos = set(
            Design.objects.filter(is_active=True)
                          .values_list('design_no', flat=True)
        )
        products = [p for p in products if p.get('design_no') in active_nos]

        return render(request, 'inventory/dashboard.html', {
            'products': products
        })
    except Exception as e:
        logger.error(f"Error rendering dashboard: {str(e)}")
        return render(request, 'inventory/error.html', {
            'error': str(e)
        })
        
        
@require_GET
def inventory_list_ajax(request):
    """
    AJAX endpoint for loading products in batches with search support
    """
    try:
        page = int(request.GET.get('page', 1))
        limit = int(request.GET.get('limit', 20))
        search_query = request.GET.get('search', '').strip()
        category_filter = request.GET.get('category', 'all')
        status_filter = request.GET.get('status', 'instock')
        
        # Get all products
        all_products = fetch_products()
        
        # Filter by active designs
        active_nos = set(
            Design.objects.filter(is_active=True).values_list('design_no', flat=True)
        )
        products = [
            prod for prod in all_products
            if prod.get('design_no') in active_nos and prod.get('design_no')
        ]
        
        # Apply search filter first (if search exists, return all matching results immediately)
        if search_query:
            filtered_products = []
            search_lower = search_query.lower()
            
            for product in products:
                # Search in design number
                if search_lower in product.get('design_no', '').lower():
                    filtered_products.append(product)
                    continue
                    
                # Search in category
                if search_lower in product.get('category', '').lower():
                    filtered_products.append(product)
                    continue
                    
                # Search in job numbers
                found_in_jobs = False
                for job in product.get('in_stock_jobs', []) + product.get('memo_jobs', []):
                    if search_lower in job.get('job_no', '').lower():
                        filtered_products.append(product)
                        found_in_jobs = True
                        break
                
                if found_in_jobs:
                    continue
            
            # For search, return all results immediately (no pagination)
            return JsonResponse({
                'success': True,
                'products': filtered_products,
                'has_more': False,
                'total_count': len(filtered_products),
                'is_search': True
            })
        
        # Apply category filter
        if category_filter != 'all':
            products = [p for p in products if p.get('category', '').lower() == category_filter.lower()]
        
        # Apply status filter
        if status_filter == 'instock':
            products = [p for p in products if p.get('in_stock_jobs')]
        elif status_filter == 'notinstock':
            products = [p for p in products if not p.get('in_stock_jobs')]
        # 'all' doesn't need filtering
        
        # Calculate pagination
        total_count = len(products)
        start_idx = (page - 1) * limit
        end_idx = start_idx + limit
        
        paginated_products = products[start_idx:end_idx]
        has_more = end_idx < total_count
        
        return JsonResponse({
            'success': True,
            'products': paginated_products,
            'has_more': has_more,
            'total_count': total_count,
            'current_page': page,
            'is_search': False
        })
        
    except Exception as e:
        logger.error(f"Error in inventory_list_ajax: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)        


def inventory_list(request):
    try:
        all_products = fetch_products()
        # print("Total fetched:", len(all_products))

        # Only active design_nos
        active_nos = set(
            Design.objects.filter(is_active=True).values_list('design_no', flat=True)
        )

        # Filter products
        filtered_products = [
            prod for prod in all_products
            if prod.get('design_no') in active_nos and prod.get('design_no')
        ]

        initial_products = filtered_products[:20]
        
        return render(request, 'inventory/inventory.html', {
            'products': initial_products,
            'has_more': len(filtered_products) > 20,
            'total_count': len(filtered_products)
        })
    except Exception as e:
        logger.error(f"Error rendering inventory: {str(e)}")
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


def wishlist_view(request):
    """Render the wishlist page for users (no login required)"""
    try:
        # Since we're using localStorage instead of database for wishlist,
        # we simply render the template without any database queries
        return render(request, 'inventory/wishlist.html')
    except Exception as e:
        logger.error(f"Error rendering wishlist page: {str(e)}")
        return render(request, 'inventory/error.html', {'error': str(e)})


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


@csrf_exempt
@require_POST
def create_order(request):
    """
    API endpoint to create a new order.
    
    Expected JSON format:
    {
        "order_items": {
            "stock": [...],
            "memo": [...],
            "custom": [...]
        },
        "payment": {
            "subtotal": 100.00,
            "shipping": 9.99,
            "tax": 8.00,
            "discount": 0.00,
            "total": 117.99
        },
        "customer": {
            "name": "John Doe",
            "email": "john.doe@example.com",
            "phone": "1234567890"
        },
        "shipping_address": {...},
        "billing_address": {...},
        "payment_method": {...}
    }
    """
    try:
        # Parse request body
        data = json.loads(request.body)
        
        # Validate required fields
        if 'order_items' not in data:
            return JsonResponse({
                'success': False,
                'error': 'Missing required field: order_items'
            }, status=400)
            
        if 'customer' not in data or 'email' not in data['customer']:
            return JsonResponse({
                'success': False,
                'error': 'Missing required customer email'
            }, status=400)
            
        # Generate order ID (in a real app, this would be a database sequence)
        order_id = f"ORD{datetime.now().strftime('%Y%m%d')}{str(uuid.uuid4())[:8].upper()}"
        
        # Create order object (would normally save to database)
        order = {
            'order_id': order_id,
            'date': datetime.now().isoformat(),
            'status': 'Pending',
            'items': data.get('order_items', {}),
            'customer': data.get('customer', {}),
            'payment': data.get('payment', {}),
            'shipping_address': data.get('shipping_address', {}),
            'billing_address': data.get('billing_address', {})
        }
        
        # In a real application, save to database here
        # For now, just log it
        logger.info(f"Created order {order_id}")
        
        # Send email notifications
        customer_email = data['customer']['email']
        admin_email = settings.ADMIN_ORDER_EMAIL
        
        # Send customer confirmation email
        customer_email_sent = send_order_confirmation_email(order, customer_email)
        if not customer_email_sent:
            logger.warning(f"Failed to send customer confirmation email for order {order_id}")
        
        # Send admin notification email
        admin_email_sent = send_admin_order_notification(order)
        if not admin_email_sent:
            logger.warning(f"Failed to send admin notification email for order {order_id}")
        
        return JsonResponse({
            'success': True,
            'order_id': order_id,
            'message': 'Order created successfully',
            'customer_email_sent': customer_email_sent,
            'admin_email_sent': admin_email_sent
        })
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON in request body'
        }, status=400)
    except Exception as e:
        logger.error(f"Error creating order: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
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
        from django.http import HttpResponse
        
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
        # Get admin email from settings
        admin_email = settings.ADMIN_ORDER_EMAIL
        
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