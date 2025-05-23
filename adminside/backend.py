# adminside/backends.py
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
from django.contrib import messages

User = get_user_model()

class CustomerAuthenticationBackend(ModelBackend):
    """
    Custom authentication backend that checks customer account status
    """
    
    def authenticate(self, request, username=None, password=None, **kwargs):
        try:
            # Try to find user by username or email
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            try:
                user = User.objects.get(email=username)
            except User.DoesNotExist:
                return None
        
        # Check password
        if user.check_password(password):
            # For staff users, always allow login
            if user.is_staff or user.is_superuser:
                return user
            
            # For customers, check their profile status
            if hasattr(user, 'customer_profile'):
                profile = user.customer_profile
                
                # Check if account is active
                if not user.is_active:
                    if request:
                        messages.error(request, 'Your account has been deactivated. Please contact support.')
                    return None
                
                # Check account status
                if profile.account_status == 'inactive':
                    if request:
                        messages.error(request, 'Your account is inactive. Please contact support.')
                    return None
                
                elif profile.account_status == 'suspended':
                    if request:
                        messages.error(request, 'Your account has been suspended. Please contact support.')
                    return None
                
                elif profile.account_status == 'pending':
                    if request:
                        messages.warning(request, 'Your account is pending approval. Please wait for activation.')
                    return None
                
                # Active status - allow login
                elif profile.account_status == 'active':
                    return user
            
            # If no profile exists, allow login (backward compatibility)
            return user
        
        return None
    
    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None