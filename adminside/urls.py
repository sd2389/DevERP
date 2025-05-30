# adminside/urls.py
from django.urls import path
from . import views

app_name = 'adminside'

urlpatterns = [
    # Login URL
    path('login/', views.admin_login, name='admin_login'),
    path('logout/', views.admin_logout, name='logout'),

    
    path('activity-log/', views.activity_log, name='activity_log'),


    # Dashboard
    path('', views.dashboard, name='dashboard'),
    path('designs/', views.design_list, name='design_list'),
    path('designs/<int:pk>/toggle/', views.toggle_design, name='toggle_design'),
    
    # Customer management - Complete URLs
    path('customers/', views.customer_list, name='customers'),
    path('customers/<int:customer_id>/', views.customer_detail, name='customer_detail'),
    path('customers/<int:customer_id>/toggle/', views.toggle_customer_status, name='toggle_customer_status'),
    path('customers/bulk-action/', views.bulk_customer_action, name='bulk_customer_action'),
    path('customers/export/', views.customer_export, name='customer_export'),
    path('customers/<int:customer_id>/notes/', views.customer_notes, name='customer_notes'),
    
    # Password reset requests
    path('password-reset-requests/', views.password_reset_requests, name='password_reset_requests'),
    path('password-reset-requests/approve/<int:req_id>/', views.approve_password_reset, name='approve_password_reset'),
    
    # Orders management
    path('orders/', views.orders_list, name='orders'),
    path('orders/<str:order_id>/', views.order_detail, name='order_detail'),
    path('orders/<str:order_id>/update/', views.update_order, name='update_order'),
    path('orders/<str:order_id>/send-emails/', views.send_order_emails, name='send_order_emails'),
    path('orders/<str:order_id>/download-pdf/', views.download_order_pdf, name='download_order_pdf'),
    
    # Inventory management
    path('inventory/', views.inventory_list, name='inventory'),
    path('inventory/add/', views.add_inventory_item, name='add_inventory'),
    path('inventory/<str:item_id>/edit/', views.edit_inventory_item, name='edit_inventory'),
    path('inventory/<str:item_id>/delete/', views.delete_inventory_item, name='delete_inventory'),
    
    # Reports
    path('reports/', views.reports, name='reports'),
    path('reports/sales/', views.sales_report, name='sales_report'),
    path('reports/inventory/', views.inventory_report, name='inventory_report'),
    
    # Export functionality
    path('orders/export/csv/', views.export_orders_csv, name='orders_export'),
    path('orders/export/pdf/', views.export_orders_pdf, name='orders_pdf_export'),
    
    # Settings
    path('settings/', views.settings, name='settings'),
    path('settings/email/', views.email_settings, name='email_settings'),
    
    # User management
    path('users/', views.users_list, name='users'),
    path('users/add/', views.add_user, name='add_user'),
    path('users/<int:user_id>/edit/', views.edit_user, name='edit_user'),
    path('pending-users/', views.pending_users, name='pending_users'),
    path('approve-user/<int:user_id>/', views.approve_user, name='approve_user'),
]