from django.urls import path
from . import views

app_name = 'adminside'

urlpatterns = [
    # Login URL (add this first, before other patterns)
    path('login/', views.admin_login, name='admin_login'),
    
    
    # Dashboard
    path('', views.dashboard, name='dashboard'),
    path('designs/', views.design_list, name='design_list'),
    path('designs/<int:pk>/toggle/', views.toggle_design, name='toggle_design'),
    
    
    
    # Orders management
    path('api/orders/', views.orders_api, name='orders_api'),
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
    
    # Customer management
    path('customers/', views.customers_list, name='customers'),
    path('customers/<int:customer_id>/', views.customer_detail, name='customer_detail'),
    
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
]