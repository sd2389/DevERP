from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_GET
import json
import logging

from .models import Product, WishlistItem

logger = logging.getLogger(__name__)

@login_required
def wishlist_view(request):
    """Render the wishlist page for logged in users"""
    try:
        # Get user's wishlist items
        wishlist_items = WishlistItem.objects.filter(user=request.user).select_related('product')
        
        # Format wishlist items for template
        items = []
        for item in wishlist_items:
            items.append({
                'id': item.id,
                'design_no': item.product.design_no,
                'category': item.product.category.name if item.product.category else '',
                'status': item.product.status,
                'added_on': item.added_on.strftime('%Y-%m-%d'),
            })
        
        context = {
            'wishlist_items': items,
            'wishlist_count': len(items)
        }
        
        return render(request, 'inventory/wishlist.html', context)
    except Exception as e:
        logger.error(f"Error rendering wishlist page: {str(e)}")
        return render(request, 'inventory/error.html', {'error': str(e)})

@require_POST
@login_required
def add_to_wishlist(request):
    """Add a product to the user's wishlist"""
    try:
        data = json.loads(request.body)
        design_no = data.get('design_no')
        
        if not design_no:
            return JsonResponse({'success': False, 'error': 'Design number is required'}, status=400)
        
        # Get product
        try:
            product = Product.objects.get(design_no=design_no)
        except Product.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Product not found'}, status=404)
        
        # Check if product is already in wishlist
        wishlist_item, created = WishlistItem.objects.get_or_create(
            user=request.user,
            product=product
        )
        
        return JsonResponse({
            'success': True,
            'created': created,
            'message': 'Product added to wishlist' if created else 'Product already in wishlist'
        })
    except Exception as e:
        logger.error(f"Error adding to wishlist: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@require_POST
@login_required
def remove_from_wishlist(request):
    """Remove a product from the user's wishlist"""
    try:
        data = json.loads(request.body)
        design_no = data.get('design_no')
        
        if not design_no:
            return JsonResponse({'success': False, 'error': 'Design number is required'}, status=400)
        
        # Remove from wishlist
        delete_count, _ = WishlistItem.objects.filter(
            user=request.user,
            product__design_no=design_no
        ).delete()
        
        return JsonResponse({
            'success': True,
            'deleted': delete_count > 0,
            'message': 'Product removed from wishlist' if delete_count > 0 else 'Product not in wishlist'
        })
    except Exception as e:
        logger.error(f"Error removing from wishlist: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)