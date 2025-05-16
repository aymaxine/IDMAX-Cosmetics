from django.urls import path
from . import views
from . import admin_views

app_name = 'users'

urlpatterns = [
    # Admin user management
    path('admin/users/', 
         admin_views.UserListView.as_view(), 
         name='admin_user_list'),
    path('admin/users/create/', 
         admin_views.UserCreateView.as_view(), 
         name='admin_user_create'),
    path('admin/users/<int:pk>/', 
         admin_views.UserDetailView.as_view(), 
         name='admin_user_detail'),
    path('admin/users/<int:pk>/update/', 
         admin_views.UserUpdateView.as_view(), 
         name='admin_user_update'),
    path('admin/users/<int:pk>/delete/', 
         admin_views.UserDeleteView.as_view(), 
         name='admin_user_delete'),
    path('admin/users/<int:pk>/reset-password/', 
         admin_views.ResetUserPasswordView.as_view(), 
         name='admin_user_reset_password'),
]