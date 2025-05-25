from django import forms
from django.contrib.auth.forms import UserCreationForm, PasswordResetForm
from .models import User

class UserRegisterForm(UserCreationForm):
    class Meta:
        model = User
        fields = ['full_name', 'username', 'mobile_no', 'company_name', 'address',
                  'city', 'state', 'country', 'zip_code', 'gst_no', 'pan_no', 'password1', 'password2']

class UserLoginForm(forms.Form):
    username = forms.EmailField(label='Email')
    password = forms.CharField(widget=forms.PasswordInput)

class CustomPasswordResetForm(PasswordResetForm):
    email = forms.EmailField(label="Email", max_length=254)
