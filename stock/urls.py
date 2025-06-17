from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('stock_list/', views.stock_list, name='stock_list'),
    path('test_email/', views.test_email, name='test_email'),
    path('item/<int:item_id>/', views.item_detail, name='item_detail'),
    path('cart/', views.cart_view, name='cart_view'),
    path('cart/remove/<int:item_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('orders/', views.order_list, name='order_list'),
    path('orders/<int:order_id>/', views.order_detail, name='order_detail'),
    path('warehouse/orders/', views.warehouse_orders, name='warehouse_orders'),
    path('cart/increase/<int:item_id>/', views.increase_item, name='increase_item'),
    path('cart/decrease/<int:item_id>/', views.decrease_item, name='decrease_item'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('login/', auth_views.LoginView.as_view(), name='login'), 
    path('accounts/password_reset/', auth_views.PasswordResetView.as_view(), name='password_reset'),
    path('accounts/password_reset/done/', auth_views.PasswordResetDoneView.as_view(), name='password_reset_done'),
    path('accounts/reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('accounts/reset/done/', auth_views.PasswordResetCompleteView.as_view(), name='password_reset_complete'),
    path('edit_item/<int:item_id>/', views.add_item, name='edit_item'),
    path('manage_stock/', views.manage_stock, name='manage_stock'),
    path('add_item/', views.add_item, name='add_item'),
    
]