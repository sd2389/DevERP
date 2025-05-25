from django.shortcuts import render, redirect
from django.contrib import messages
from .models import User
from django.contrib.auth.hashers import make_password

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
