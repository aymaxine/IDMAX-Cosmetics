from django.shortcuts import render
from django.core.exceptions import PermissionDenied
from django.http import Http404
import logging

# Set up logging
logger = logging.getLogger(__name__)

def handler404(request, exception=None):
    """Handle 404 Page Not Found errors."""
    return render(request, 'store/errors/404.html', status=404)

def handler500(request):
    """Handle 500 Server Error errors."""
    return render(request, 'store/errors/500.html', status=500)

def handler403(request, exception=None):
    """Handle 403 Forbidden errors."""
    return render(request, 'store/errors/403.html', status=403)

def error_test(request):
    """View to show test links for error pages."""
    return render(request, 'store/error_test.html')

def test_404(request):
    """View to test 404 error page."""
    raise Http404("Page not found")

def test_500(request):
    """View to test 500 error page."""
    raise Exception("Server error")

def test_403(request):
    """View to test 403 error page."""
    raise PermissionDenied("Permission denied")