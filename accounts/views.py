# accounts/views.py
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.core.mail import send_mail
from django.db import IntegrityError, transaction
from django.contrib.auth import get_user_model
from django.utils import timezone
from .forms import RegistrationForm, UserLoginForm
from .models import PasswordResetRequest

User = get_user_model()

def register(request):
    errors = []
    
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        
        if form.is_valid():
            try:
                with transaction.atomic():
                    # Create user with email as username
                    user = form.save(commit=False)
                    user.is_active = False  # Require admin approval
                    user.save()
                    
                    # Send notification email to admin
                    send_mail(
                        'New User Registration - Approval Required',
                        f'New user {user.full_name} ({user.email}) has registered and requires approval.',
                        'noreply@deverp.com',
                        ['admin@deverp.com'],  # Admin email
                        fail_silently=True,
                    )
                    
                    messages.success(
                        request, 
                        "Registration successful! Your account is pending admin approval. You'll receive an email once approved."
                    )
                    return redirect('accounts:login')
                    
            except IntegrityError as e:
                # Handle duplicate email gracefully
                if 'username' in str(e):
                    errors.append("An account with this email already exists.")
                else:
                    errors.append("Registration failed. Please try again.")
                    
        else:
            # Collect form errors
            for field, field_errors in form.errors.items():
                for error in field_errors:
                    if field == '__all__':
                        errors.append(error)
                    else:
                        errors.append(f"{form.fields.get(field, field).label}: {error}")
    else:
        form = RegistrationForm()
    
    return render(request, 'accounts/register.html', {
        'form': form,
        'errors': errors
    })


def login_view(request):
    if request.user.is_authenticated:
        return redirect('inventory:inventory')
        
    if request.method == 'POST':
        form = UserLoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']  # This is actually the email
            password = form.cleaned_data['password']
            
            user = authenticate(request, username=username, password=password)
            
            if user is not None:
                if user.is_active:
                    login(request, user)
                    
                    # Redirect based on user type
                    if user.is_superuser or user.is_staff:
                        return redirect('adminside:dashboard')
                    else:
                        return redirect('inventory:inventory')
                else:
                    messages.error(
                        request, 
                        "Your account is pending approval. Please wait for admin activation."
                    )
            else:
                messages.error(request, "Invalid email or password.")
    else:
        form = UserLoginForm()
    
    return render(request, 'accounts/login.html', {'form': form})


def logout_view(request):
    logout(request)
    messages.success(request, "You have been successfully logged out.")
    return redirect('accounts:login')


def request_password_reset(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        
        if email:
            user = User.objects.filter(email=email).first()
            
            if user:
                # Check if there's already a pending request
                pending_request = PasswordResetRequest.objects.filter(
                    user=user, 
                    is_approved=False
                ).first()
                
                if pending_request:
                    messages.info(
                        request, 
                        "A password reset request is already pending for this account."
                    )
                else:
                    # Create new request
                    PasswordResetRequest.objects.create(user=user)
                    
                    # Notify admin
                    send_mail(
                        'Password Reset Request',
                        f'User {user.full_name} ({user.email}) has requested a password reset.',
                        'noreply@deverp.com',
                        ['admin@deverp.com'],
                        fail_silently=True,
                    )
                    
                    messages.success(
                        request, 
                        "Password reset requested. You will receive an email once approved by admin."
                    )
            else:
                messages.error(request, "No account found with that email address.")
        else:
            messages.error(request, "Please enter a valid email address.")
            
    return render(request, 'accounts/request_password_reset.html')


def approve_password_reset(request, req_id):
    """Admin function to approve password reset"""
    if not request.user.is_staff:
        messages.error(request, "You don't have permission to access this page.")
        return redirect('accounts:login')
        
    try:
        reset_request = PasswordResetRequest.objects.get(id=req_id)
        
        if reset_request.is_approved:
            messages.info(request, "This password reset has already been processed.")
        else:
            # Generate temporary password
            temp_password = User.objects.make_random_password(length=10)
            
            # Update user password
            user = reset_request.user
            user.set_password(temp_password)
            user.save()
            
            # Mark request as approved
            reset_request.is_approved = True
            reset_request.processed_at = timezone.now()
            reset_request.save()
            
            # Send email with temporary password
            send_mail(
                'Your Password Has Been Reset',
                f'''Hello {user.full_name},

                    Your password reset request has been approved.

                    Your temporary password is: {temp_password}

                    Please login with this temporary password and change it immediately.

                    Best regards,
                    DevERP Team''',
                'noreply@deverp.com',
                [user.email],
                fail_silently=False,
            )
            
            messages.success(
                request, 
                f"Password reset for {user.full_name} completed. Email sent with temporary password."
            )
            
    except PasswordResetRequest.DoesNotExist:
        messages.error(request, "Password reset request not found.")
        
    return redirect('adminside:password_reset_requests')