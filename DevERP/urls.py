# DevERP/urls.py
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
from . import views  # Import your views

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Auth views
    path('accounts/login/', auth_views.LoginView.as_view(template_name='auth/login.html'), name='login'),
    path('accounts/logout/', auth_views.LogoutView.as_view(), name='logout'),
    
    # App URLs
    path('adminside/', include('adminside.urls')),
    path('inventory/', include('inventory.urls')),
    path('orders/', include('orders.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Custom error handlers - this must be at module level, not inside a function or conditional
handler404 = 'DevERP.views.handler404'
handler500 = 'DevERP.views.handler500'