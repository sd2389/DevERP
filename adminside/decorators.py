# adminside/decorators.py

from django.contrib.auth.decorators import user_passes_test
from django.conf import settings
from django.shortcuts import redirect
from django.urls import reverse
from functools import wraps

def admin_login_required(function):
    """
    Decorator for views that checks that the user is logged in and is staff,
    redirecting to the admin login page if necessary.
    """
    @wraps(function)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated or not request.user.is_staff:
            return redirect(f"{reverse('admin_login')}?next={request.path}")
        return function(request, *args, **kwargs)
    return wrapper