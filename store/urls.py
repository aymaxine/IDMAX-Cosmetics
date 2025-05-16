from django.urls import path, re_path
from django.views.generic.base import RedirectView
from . import views
from . import admin_views

app_name = 'store'

urlpatterns = [
    # Public views
    path('', views.home, name='home'),
    path('about/', views.about, name='about'),
    path('contact/', views.contact, name='contact'),
    path('404/', RedirectView.as_view(pattern_name='store:home', permanent=False), name='404_redirect'),
    path('products/', views.ProductListView.as_view(), name='product_list'),
    path('oproduct/', RedirectView.as_view(pattern_name='store:product_list', permanent=False), name='oproduct_redirect'),
    re_path(r'^products/category=(?P<category_id>\d+)$', views.category_redirect, name='category_redirect'),
    re_path(r'^products/sort=(?P<sort_option>\w+)$', views.sort_redirect, name='sort_redirect'),
    path('products/<int:pk>/', views.ProductDetailView.as_view(), name='product_detail'),
    path('products/<int:product_id>/review/', views.add_review, name='add_review'),


    # Cart views
    path('cart/', views.cart_detail, name='cart_detail'),
    path('cart/add/<int:product_id>/', views.cart_add, name='cart_add'),
    path('cart/remove/<int:product_id>/', views.cart_remove, name='cart_remove'),

    # Wishlist views
    path('wishlist/', views.wishlist_detail, name='wishlist_detail'),
    path('wishlist/add/<int:product_id>/', views.wishlist_add, name='wishlist_add'),
    path('wishlist/remove/<int:product_id>/', views.wishlist_remove, name='wishlist_remove'),

    # Comparison views
    path('compare/', views.comparison_list_detail, name='comparison_list'),
    path('compare/add/<int:product_id>/', views.comparison_add, name='comparison_add'),
    path('compare/remove/<int:product_id>/', views.comparison_remove, name='comparison_remove'),
    path('compare/clear/', views.comparison_clear, name='comparison_clear'),

    # Order views
    path('orders/', views.order_list, name='order_list'),
    path('orders/<int:order_id>/', views.order_detail, name='order_detail'),
    path('orders/<int:order_id>/cancel/', views.order_cancel, name='order_cancel'),
    path('checkout/', views.order_create, name='order_create'),
    path('apply-coupon/', views.coupon_apply, name='coupon_apply'),
    path('review/delete/<int:review_id>/', views.delete_review, name='delete_review'),    # Admin views
    path('store-admin/dashboard/', views.AdminDashboardView.as_view(), name='admin_dashboard'),
    path('store-admin/orders/', views.AdminOrderListView.as_view(), name='admin_order_list'),
    path('store-admin/orders/<int:pk>/update/', views.AdminOrderUpdateView.as_view(), name='admin_order_update'),
    path('store-admin/orders/<int:pk>/', views.AdminOrderDetailView.as_view(), name='admin_order_detail'),
    path('store-admin/users/', admin_views.UserListView.as_view(), name='admin_user_list'),
      # Admin Product Management
    path('store-admin/products/', 
         admin_views.ProductListView.as_view(), 
         name='admin_product_list'),
    path('store-admin/products/create/', 
         admin_views.ProductCreateView.as_view(), 
         name='admin_product_create'),
    path('store-admin/products/<int:pk>/', 
         admin_views.ProductDetailView.as_view(), 
         name='admin_product_detail'),
    path('store-admin/products/<int:pk>/update/', 
         admin_views.ProductUpdateView.as_view(), 
         name='admin_product_update'),
    path('store-admin/products/<int:pk>/delete/', 
         admin_views.ProductDeleteView.as_view(), 
         name='admin_product_delete'),
         
    # Admin Category Management
    path('store-admin/categories/', 
         admin_views.CategoryListView.as_view(), 
         name='admin_category_list'),
    path('store-admin/categories/create/', 
         admin_views.CategoryCreateView.as_view(), 
         name='admin_category_create'),
    path('store-admin/categories/<int:pk>/update/', 
         admin_views.CategoryUpdateView.as_view(), 
         name='admin_category_update'),
    path('store-admin/categories/<int:pk>/delete/', 
         admin_views.CategoryDeleteView.as_view(), 
         name='admin_category_delete'),
]