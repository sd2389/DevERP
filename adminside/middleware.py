# adminside/middleware.py
from django.shortcuts import redirect
from django.urls import resolve

class AdminAccessMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Check if path is in admin area
        if request.path.startswith('/adminside/') and not request.path.startswith('/adminside/login/'):
            # If user is not authenticated or not staff, redirect to login
            if not request.user.is_authenticated or not request.user.is_staff:
                # Include the original path as 'next' parameter
                return redirect(f'/adminside/login/?next={request.path}')
        
        return self.get_response(request)