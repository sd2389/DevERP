# accounts/forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm, PasswordResetForm
from .models import User

class RegistrationForm(forms.ModelForm):
    password1 = forms.CharField(
        label='Password',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Create a strong password'})
    )
    password2 = forms.CharField(
        label='Confirm Password',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Confirm your password'})
    )
    
    # Email field that will be used as username
    email = forms.EmailField(
        label='Email Address',
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'john@example.com'})
    )

    class Meta:
        model = User
        fields = [
            'email', 'full_name', 'mobile_no', 'company_name',
            'address', 'city', 'state', 'zip_code', 'country', 
            'gst_no', 'pan_no'
        ]
        widgets = {
            'full_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'John Doe'}),
            'mobile_no': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+1 (555) 123-4567'}),
            'company_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Acme Corporation'}),
            'address': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '123 Main Street'}),
            'city': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'New York'}),
            'state': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'NY'}),
            'zip_code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '10001'}),
            'country': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'United States'}),
            'gst_no': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'GST Number (Optional)'}),
            'pan_no': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'PAN Number (Optional)'}),
        }

    def clean_email(self):
        email = self.cleaned_data.get('email')
        # Check if email is already used as username
        if User.objects.filter(username=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get('password1')
        password2 = cleaned_data.get('password2')

        if password1 and password2:
            if password1 != password2:
                raise forms.ValidationError("Passwords do not match.")
            
            # Password strength validation
            if len(password1) < 8:
                raise forms.ValidationError("Password must be at least 8 characters long.")
            
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        # Use email as username
        user.username = self.cleaned_data['email']
        user.email = self.cleaned_data['email']
        user.set_password(self.cleaned_data['password1'])
        
        if commit:
            user.save()
        return user


class UserLoginForm(forms.Form):
    username = forms.EmailField(
        label='Email',
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email Address'})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Password'})
    )


class CustomPasswordResetForm(PasswordResetForm):
    email = forms.EmailField(
        label="Email", 
        max_length=254,
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Enter your email'})
    )