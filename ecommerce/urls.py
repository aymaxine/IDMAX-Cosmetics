"""
URL configuration for IDMAX Cosmetics Ecommerce project.
"""
from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
from users import views as user_views
from django.views.defaults import page_not_found
from ecommerce import views as ecommerce_views
from django.views.static import serve

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('store.urls')),
    # path('users/', include('users.urls')),
    
    # Test error pages
    path('error-test/', ecommerce_views.error_test, name='error_test'),
    path('test-404/', ecommerce_views.test_404, name='test_404'),
    path('test-500/', ecommerce_views.test_500, name='test_500'),
    path('test-403/', ecommerce_views.test_403, name='test_403'),

    # Authentication
    path('register/', user_views.register, name='register'),
    path('profile/', user_views.profile, name='profile'),
    path('login/', auth_views.LoginView.as_view(template_name='users/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(template_name='users/logout.html'), name='logout'),

    # Password reset
    path('password-reset/', 
         auth_views.PasswordResetView.as_view(template_name='users/password_reset.html'), 
         name='password_reset'),
    path('password-reset/done/', 
         auth_views.PasswordResetDoneView.as_view(template_name='users/password_reset_done.html'), 
         name='password_reset_done'),
    path('password-reset-confirm/<uidb64>/<token>/', 
         auth_views.PasswordResetConfirmView.as_view(template_name='users/password_reset_confirm.html'), 
         name='password_reset_confirm'),
    path('password-reset-complete/', 
         auth_views.PasswordResetCompleteView.as_view(template_name='users/password_reset_complete.html'), 
         name='password_reset_complete'),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
else:
    # In production, serve files from STATIC_ROOT
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# Define custom error handlers
handler404 = 'ecommerce.views.handler404'
handler500 = 'ecommerce.views.handler500'
handler403 = 'ecommerce.views.handler403'

# Only add these URL patterns if DEBUG is False and INSECURE_SERVE_STATIC_FILES_BY_DJANGO is True
# Or if DEBUG is True (though Django's dev server handles it then, this ensures consistency if INSECURE is also True)
if not settings.DEBUG and getattr(settings, 'INSECURE_SERVE_STATIC_FILES_BY_DJANGO', False):
    urlpatterns += [
        re_path(r'^%s(?P<path>.*)$' % settings.MEDIA_URL.lstrip('/'), serve, {
            'document_root': settings.MEDIA_ROOT,
        }),
        re_path(r'^%s(?P<path>.*)$' % settings.STATIC_URL.lstrip('/'), serve, {  # Add this for static files
            'document_root': settings.STATIC_ROOT,
        }),
    ]
elif settings.DEBUG:
    from django.conf.urls.static import static
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)