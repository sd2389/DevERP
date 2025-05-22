from django.http import JsonResponse
from django.views.decorators.http import require_GET
from django.views.decorators.cache import cache_page
import json
import logging
from inventory.models import Design
from .services import DevJewelsAPIService

logger = logging.getLogger(__name__)

@require_GET
@cache_page(60 * 15)  # Cache for 15 minutes
def get_inventory_filters(request):
    """
    Get all filter options for inventory based on DevJewels API data
    """
    try:
        # Get filter options from service
        filters = DevJewelsAPIService.get_filter_options()
        
        return JsonResponse({
            'success': True,
            **filters
        })
    except Exception as e:
        logger.error(f"Error getting inventory filters: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@require_GET
def get_inventory_data(request):
    """
    Get inventory data from DevJewels APIs with filtering, sorting, and pagination
    """
    try:
        # Extract filter parameters from request
        filters = {
            'category': request.GET.get('category', ''),
            'gender': request.GET.get('gender', ''),
            'collection': request.GET.get('collection', ''),
            'subcategory': request.GET.get('subcategory', ''),
            'producttype': request.GET.get('producttype', '')
        }
        
        # Get status filter
        status = request.GET.get('status', '')
        if status:
            filters['status'] = status
            
        # Get search term
        search = request.GET.get('search', '')
        
        # Get pagination parameters
        page = int(request.GET.get('page', 1))
        per_page = int(request.GET.get('per_page', 50))
        
        # Get sorting parameters
        sort_by = request.GET.get('sort_by', 'design_no')
        sort_dir = request.GET.get('sort_dir', 'asc')
        
        # Check for refresh parameter to bypass cache
        refresh = request.GET.get('refresh', '').lower() == 'true'
        
        # Get filtered products
        if refresh:
            # Force refresh of data
            DevJewelsAPIService.get_combined_inventory_data(refresh=True)
            
        result = DevJewelsAPIService.filter_products(
            filters=filters,
            search=search,
            sort_by=sort_by,
            sort_dir=sort_dir,
            page=page,
            per_page=per_page
        )
        
        return JsonResponse({
            'success': True,
            **result
        })
    except Exception as e:
        logger.error(f"Error getting inventory data: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@require_GET
@cache_page(60 * 5)  # Cache for 5 minutes
def get_product_detail(request, design_no):
    """
    Get detailed information for a specific product from DevJewels API
    """
    try:
        product = DevJewelsAPIService.get_product_by_design_no(design_no)
        
        if not product:
            return JsonResponse({
                'success': False,
                'error': f"Product with design_no '{design_no}' not found"
            }, status=404)
        
        return JsonResponse({
            'success': True,
            'product': product
        })
    except Exception as e:
        logger.error(f"Error getting product detail: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)
        
def fetch_products():
    # Get external inventory
    response = requests.get("https://admin.devjewels.com/mobileapi/api_stock.php")
    data = response.json()

    # ✅ Efficient lookup of visible designs
    active_designs = set(
        Design.objects.filter(is_active=True).values_list("design_no", flat=True)
    )

    products = []
    for job in data:
        design_no = job.get("design_no")

        # ✅ Skip inactive designs
        if design_no not in active_designs:
            continue

        products.append({
            "job_id": job.get("job_id"),
            "design_no": design_no,
            "job_no": job.get("job_no"),
            "metal_type": job.get("metal_type"),
            "metal_quality": job.get("metal_quality"),
            "gwt": job.get("gwt"),
            "nwt": job.get("nwt"),
            "dwt": job.get("dwt"),
            "dpcs": job.get("dpcs"),
            "size": job.get("size"),
            "memostock": job.get("memostock"),
            "totamt": job.get("totamt"),
        })

    return products