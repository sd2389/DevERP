from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.urls import reverse_lazy
from django.contrib.auth.views import PasswordResetView   # <-- THIS LINE
from django.contrib.auth.views import (
    PasswordResetView, PasswordResetDoneView,
    PasswordResetConfirmView, PasswordResetCompleteView
)
from .models import User


def register(request):
    if request.method == 'POST':
        data = request.POST
        errors = []

        required = ['full_name', 'username', 'mobile_no', 'company_name', 'address', 'city', 'state', 'country', 'zip_code', 'password1', 'password2']
        for field in required:
            if not data.get(field, '').strip():
                errors.append(f"{field.replace('_', ' ').title()} is required.")
        
        if data['password1'] != data['password2']:
            errors.append("Passwords do not match.")

        if User.objects.filter(username=data['username']).exists():
            errors.append("Email already exists.")

        if errors:
            return render(request, 'accounts/register.html', {'errors': errors, 'form': data})

        user = User.objects.create(
            username=data['username'],
            full_name=data['full_name'],
            mobile_no=data['mobile_no'],
            company_name=data['company_name'],
            address=data['address'],
            city=data['city'],
            state=data['state'],
            country=data['country'],
            zip_code=data['zip_code'],
            gst_no=data.get('gst_no', ''),
            pan_no=data.get('pan_no', ''),
            password=make_password(data['password1']),
        )
        messages.success(request, "Registration successful. You can now log in.")
        return redirect('login')  # set to your login URL name

    return render(request, 'accounts/register.html')

def login_view(request):
    if request.method == 'POST':
        username = request.POST['username']  # Email field
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('inventory:inventory')  # Or your dashboard
        else:
            messages.error(request, 'Invalid email or password')
    return render(request, 'accounts/login.html')

# class CustomPasswordResetView(PasswordResetView):
#     form_class = CustomPasswordResetForm
#     template_name = 'accounts/password_reset.html'
#     email_template_name = 'accounts/password_reset_email.html'
#     subject_template_name = 'accounts/password_reset_subject.txt'
#     success_url = reverse_lazy('accounts:password_reset_done')
    
class CustomPasswordResetView(PasswordResetView):
    template_name = 'accounts/password_reset.html'
    # ... other config

class CustomPasswordResetDoneView(PasswordResetDoneView):
    template_name = 'accounts/password_reset_done.html'

class CustomPasswordResetConfirmView(PasswordResetConfirmView):
    template_name = 'accounts/password_reset_confirm.html'

class CustomPasswordResetCompleteView(PasswordResetCompleteView):
    template_name = 'accounts/password_reset_complete.html'
    
def custom_password_reset_request(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        user_model = get_user_model()
        try:
            user = user_model.objects.get(username=email)
            # Prevent duplicate pending requests for same user
            if not PasswordResetRequest.objects.filter(user=user, is_approved=False).exists():
                PasswordResetRequest.objects.create(user=user)
                messages.success(request, "Your password reset request has been submitted and awaits admin approval.")
            else:
                messages.info(request, "You already have a pending password reset request.")
        except user_model.DoesNotExist:
            messages.error(request, "No user found with that email address.")
        return redirect('accounts:login')
    return render(request, 'accounts/password_reset.html')