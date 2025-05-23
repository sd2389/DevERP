from django.urls import path
from django.http import JsonResponse
from . import views

app_name = 'inventory'

urlpatterns = [
    path('', views.inventory_list, name='inventory'),
    path('cart/', views.cart_view, name='cart'),
    path('wishlist/', views.wishlist_view, name='wishlist'),
    path('dashboard/', views.inventory_dashboard, name='dashboard'),
    path('orders/', views.order_view, name='orders'),
    path('ajax/products/', views.inventory_list_ajax, name='inventory_ajax'),

    # API endpoint for stock data
    path('api/get-stock-by-job/<str:job_no>/', views.get_stock_by_job, name='api_stock_by_job'),
    path('api/get-stock-by-design/<str:design_no>/', views.get_stock_by_design, name='api_stock_by_design'),
    
    # Admin routes for email management
    path('admin/orders//send-emails/', views.send_order_emails, name='admin_send_order_emails'),
    path('admin/orders//download-pdf/', views.download_order_pdf, name='admin_download_order_pdf'),
]