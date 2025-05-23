# DevERP/auth_views.py
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.models import User
from django.db.models import Q
from django.core.exceptions import MultipleObjectsReturned

def login_view(request):
    """Handle user login with email or username support"""
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        user_type = request.POST.get('user_type', 'customer')
        
        if not username or not password:
            messages.error(request, 'Please provide both username/email and password.')
            return render(request, 'auth/login.html')
        
        # First try direct authentication with username
        user = authenticate(request, username=username, password=password)
        
        # If failed, check if input is email and try email-based auth
        if not user and '@' in username:
            try:
                # Use filter().first() to avoid MultipleObjectsReturned
                user_obj = User.objects.filter(email=username).first()
                
                if user_obj:
                    # Authenticate using the username of found user
                    user = authenticate(request, username=user_obj.username, password=password)
                    
                    # If multiple users with same email exist, warn user
                    if User.objects.filter(email=username).count() > 1:
                        messages.warning(request, 'Multiple accounts found with this email. Please use your username instead.')
                
            except Exception as e:
                messages.error(request, 'An error occurred during login. Please try again.')
                return render(request, 'auth/login.html')
        
        if user is not None:
            # Check if user is active
            if not user.is_active:
                messages.error(request, 'Your account has been disabled.')
                return render(request, 'auth/login.html')
            
            # Check user type if you have custom user types
            # Example: if hasattr(user, 'userprofile') and user.userprofile.user_type != user_type:
            #     messages.error(request, f'Invalid login for {user_type} portal.')
            #     return render(request, 'auth/login.html')
            
            login(request, user)
            messages.success(request, f'Welcome back, {user.get_full_name() or user.username}!')
            
            # Redirect to next URL if provided, otherwise dashboard
            next_url = request.GET.get('next', 'dashboard')
            return redirect(next_url)
        else:
            messages.error(request, 'Invalid username/email or password.')
    
    return render(request, 'auth/login.html')


def logout_view(request):
    """Handle user logout"""
    logout(request)
    messages.success(request, 'You have been successfully logged out.')
    return redirect('login')


def signup_view(request):
    """Handle user registration"""
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip().lower()
        password = request.POST.get('password', '')
        confirm_password = request.POST.get('confirm_password', '')
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        
        # Validation
        errors = []
        
        if not username or not email or not password:
            errors.append('All fields are required.')
        
        if password != confirm_password:
            errors.append('Passwords do not match.')
        
        if len(password) < 8:
            errors.append('Password must be at least 8 characters long.')
        
        if User.objects.filter(username=username).exists():
            errors.append('Username already exists.')
        
        if User.objects.filter(email=email).exists():
            errors.append('Email already registered.')
        
        if errors:
            for error in errors:
                messages.error(request, error)
            return render(request, 'auth/signup.html', {
                'username': username,
                'email': email,
                'first_name': first_name,
                'last_name': last_name,
            })
        
        try:
            # Create user
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name
            )
            
            # Auto-login after signup
            login(request, user)
            messages.success(request, 'Account created successfully! Welcome to DevERP.')
            return redirect('dashboard')
            
        except Exception as e:
            messages.error(request, 'An error occurred during registration. Please try again.')
            return render(request, 'auth/signup.html')
    
    return render(request, 'auth/signup.html')


def password_reset_view(request):
    """Handle password reset requests"""
    if request.method == 'POST':
        email = request.POST.get('email', '').strip().lower()
        
        if not email:
            messages.error(request, 'Please provide your email address.')
            return render(request, 'auth/password_reset.html')
        
        # Check if email exists
        users = User.objects.filter(email=email)
        
        if not users.exists():
            messages.error(request, 'No account found with this email address.')
        elif users.count() > 1:
            messages.error(request, 'Multiple accounts found with this email. Please contact support.')
        else:
            # TODO: Implement actual password reset logic
            # For now, just show success message
            messages.success(request, 'Password reset link has been sent to your email.')
            return redirect('login')
    
    return render(request, 'auth/password_reset.html')