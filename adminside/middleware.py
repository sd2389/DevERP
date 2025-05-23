# Create a middleware to control admin access
# adminside/middleware.py

from django.shortcuts import redirect
from django.urls import resolve, reverse
from django.conf import settings
from django.contrib import messages

class AdminAccessMiddleware:
    """
    Middleware to restrict access to admin areas based on user permissions
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        
    def __call__(self, request):
        # Continue if user is not authenticated
        if not request.user.is_authenticated:
            return self.get_response(request)
            
        # Check if the URL is in the admin area
        path = request.path_info
        
        # If this is an admin path
        if path.startswith('/adminside/'):
            # Check if user has staff permissions
            if not request.user.is_staff:
                # User doesn't have admin permission, redirect to their dashboard
                messages.error(request, 'You do not have permission to access the admin area.')
                return redirect('inventory:inventory')
                
        # Process the request normally for other URLs
        return self.get_response(request)