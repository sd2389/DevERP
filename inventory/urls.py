# application/vnd.ant.code language="python"
# Update the urls.py file to include the new endpoints
from django.urls import path
from . import views

app_name = 'inventory'

urlpatterns = [
    path('', views.inventory_list, name='inventory'),
    path('cart/', views.cart_view, name='cart'),
    path('wishlist/', views.wishlist_view, name='wishlist'),
    path('dashboard/', views.inventory_dashboard, name='dashboard'),
    path('orders/', views.order_view, name='orders'),
    
    # Fixed AJAX endpoint URL
    path('ajax/', views.inventory_list_ajax, name='inventory_ajax'),
    
    # Add the filter-options endpoint
    path('api/filter-options/', views.get_filter_options, name='api_filter_options'),
    
    # Existing API endpoints
    path('api/get-stock-by-job/<str:job_no>/', views.get_stock_by_job, name='api_stock_by_job'),
    path('api/get-stock-by-design/<str:design_no>/', views.get_stock_by_design, name='api_stock_by_design'),
    
    # Admin routes
    path('admin/orders//send-emails/', views.send_order_emails, name='admin_send_order_emails'),
    path('admin/orders//download-pdf/', views.download_order_pdf, name='admin_download_order_pdf'),
]