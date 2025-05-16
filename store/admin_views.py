from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView
from django.urls import reverse_lazy, reverse
from django.contrib import messages
from django.db.models import Count, Sum, Q, F
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.contrib.auth.models import User

from .models import Product, Category, ProductImage, Order
from .forms import ProductForm, ProductImageFormSet, CategoryForm
from users.models import Profile


class AdminRequiredMixin(UserPassesTestMixin):
    """Mixin to check if user is admin/staff"""
    def test_func(self):
        return self.request.user.is_staff


class ProductListView(LoginRequiredMixin, AdminRequiredMixin, ListView):
    model = Product
    template_name = 'store/admin/product_list.html'
    context_object_name = 'products'
    paginate_by = 10

    def get_queryset(self):
        queryset = super().get_queryset()
        search_query = self.request.GET.get('search', '')
        category_filter = self.request.GET.get('category', '')
        
        if search_query:
            queryset = queryset.filter(
                Q(name__icontains=search_query) | 
                Q(description__icontains=search_query)
            )
        
        if category_filter:
            queryset = queryset.filter(category_id=category_filter)
            
        return queryset.order_by('-updated_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = Category.objects.all()
        context['search_query'] = self.request.GET.get('search', '')
        context['category_filter'] = self.request.GET.get('category', '')
        return context


class ProductCreateView(LoginRequiredMixin, AdminRequiredMixin, CreateView):
    model = Product
    form_class = ProductForm
    template_name = 'store/admin/product_form.html'
    success_url = reverse_lazy('store:admin_product_list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['image_formset'] = ProductImageFormSet(
                self.request.POST, 
                self.request.FILES
            )
        else:
            context['image_formset'] = ProductImageFormSet()
        return context
    
    def form_valid(self, form):
        context = self.get_context_data()
        image_formset = context['image_formset']
        
        if form.is_valid() and image_formset.is_valid():
            self.object = form.save()
            
            # Save formset with connection to the product
            image_formset.instance = self.object
            image_formset.save()
            
            messages.success(self.request, f"Product '{self.object.name}' created successfully")
            return super().form_valid(form)
        else:
            return self.form_invalid(form)


class ProductUpdateView(LoginRequiredMixin, AdminRequiredMixin, UpdateView):
    model = Product
    form_class = ProductForm
    template_name = 'store/admin/product_form.html'
    
    def get_success_url(self):
        return reverse('store:admin_product_detail', kwargs={'pk': self.object.pk})
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['image_formset'] = ProductImageFormSet(
                self.request.POST, 
                self.request.FILES,
                instance=self.object
            )
        else:
            context['image_formset'] = ProductImageFormSet(instance=self.object)
        return context
    
    def form_valid(self, form):
        context = self.get_context_data()
        image_formset = context['image_formset']
        
        if form.is_valid() and image_formset.is_valid():
            self.object = form.save()
            
            # Save formset with connection to the product
            image_formset.instance = self.object
            image_formset.save()
            
            messages.success(self.request, f"Product '{self.object.name}' updated successfully")
            return super().form_valid(form)
        else:
            return self.form_invalid(form)


class ProductDetailView(LoginRequiredMixin, AdminRequiredMixin, DetailView):
    model = Product
    template_name = 'store/admin/product_detail.html'
    context_object_name = 'product'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['images'] = self.object.additional_images.all()
        # Get order data for this product
        context['order_count'] = Order.objects.filter(items__product=self.object).distinct().count()
        return context


class ProductDeleteView(LoginRequiredMixin, AdminRequiredMixin, DeleteView):
    model = Product
    template_name = 'store/admin/product_confirm_delete.html'
    success_url = reverse_lazy('store:admin_product_list')
    
    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        product_name = self.object.name
        success_url = self.get_success_url()
        self.object.delete()
        messages.success(self.request, f"Product '{product_name}' deleted successfully")
        return redirect(success_url)


class CategoryListView(LoginRequiredMixin, AdminRequiredMixin, ListView):
    model = Category
    template_name = 'store/admin/category_list.html'
    context_object_name = 'categories'
    paginate_by = 20
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add product count for each category
        categories_with_count = []
        for category in context['categories']:
            product_count = Product.objects.filter(category=category).count()
            categories_with_count.append({
                'category': category,
                'product_count': product_count
            })
        context['categories_with_count'] = categories_with_count
        return context


class CategoryCreateView(LoginRequiredMixin, AdminRequiredMixin, CreateView):
    model = Category
    form_class = CategoryForm
    template_name = 'store/admin/category_form.html'
    success_url = reverse_lazy('store:admin_category_list')
    
    def form_valid(self, form):
        self.object = form.save()
        messages.success(self.request, f"Category '{self.object.name}' created successfully")
        return super().form_valid(form)


class CategoryUpdateView(LoginRequiredMixin, AdminRequiredMixin, UpdateView):
    model = Category
    form_class = CategoryForm
    template_name = 'store/admin/category_form.html'
    success_url = reverse_lazy('store:admin_category_list')
    
    def form_valid(self, form):
        self.object = form.save()
        messages.success(self.request, f"Category '{self.object.name}' updated successfully")
        return super().form_valid(form)


class CategoryDeleteView(LoginRequiredMixin, AdminRequiredMixin, DeleteView):
    model = Category
    template_name = 'store/admin/category_confirm_delete.html'
    success_url = reverse_lazy('store:admin_category_list')
    
    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        category_name = self.object.name
        success_url = self.get_success_url()
        
        # Check if category has products
        product_count = Product.objects.filter(category=self.object).count()
        if product_count > 0:
            messages.error(self.request, f"Cannot delete category '{category_name}' as it contains {product_count} products")
            return redirect(success_url)
        
        self.object.delete()
        messages.success(self.request, f"Category '{category_name}' deleted successfully")
        return redirect(success_url)


class UserListView(LoginRequiredMixin, AdminRequiredMixin, ListView):
    """Admin view for listing and managing users"""
    model = User
    template_name = 'store/admin/user_list.html'
    context_object_name = 'users'
    paginate_by = 15

    def get_queryset(self):
        queryset = super().get_queryset()
        search_query = self.request.GET.get('search', '')
        role_filter = self.request.GET.get('role', '')
        status_filter = self.request.GET.get('status', '')
        
        # Apply search filter
        if search_query:
            queryset = queryset.filter(
                Q(username__icontains=search_query) |
                Q(email__icontains=search_query) |
                Q(first_name__icontains=search_query) |
                Q(last_name__icontains=search_query)
            )
            
        # Apply role filter
        if role_filter == 'staff':
            queryset = queryset.filter(is_staff=True)
        elif role_filter == 'admin':
            queryset = queryset.filter(is_superuser=True)
        elif role_filter == 'customer':
            queryset = queryset.filter(is_staff=False, is_superuser=False)
            
        # Apply status filter
        if status_filter == 'active':
            queryset = queryset.filter(is_active=True)
        elif status_filter == 'inactive':
            queryset = queryset.filter(is_active=False)
            
        # Sort by join date (newest first by default)
        sort_by = self.request.GET.get('sort', '-date_joined')
        if sort_by == 'username':
            queryset = queryset.order_by('username')
        elif sort_by == 'email':
            queryset = queryset.order_by('email')
        elif sort_by == 'active':
            queryset = queryset.order_by('-is_active', '-date_joined')
        elif sort_by == 'staff':
            queryset = queryset.order_by('-is_staff', '-date_joined')
        else:
            queryset = queryset.order_by('-date_joined')
            
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['total_users'] = User.objects.count()
        context['active_users'] = User.objects.filter(is_active=True).count()
        context['staff_users'] = User.objects.filter(is_staff=True).count()
        context['superuser_count'] = User.objects.filter(is_superuser=True).count()
        context['customer_count'] = User.objects.filter(is_staff=False, is_superuser=False).count()
        context['inactive_count'] = User.objects.filter(is_active=False).count()
        
        # Get filter parameters for maintaining filter state in the form
        context['search_query'] = self.request.GET.get('search', '')
        context['current_sort'] = self.request.GET.get('sort', '-date_joined')
        context['current_role'] = self.request.GET.get('role', '')
        context['current_status'] = self.request.GET.get('status', '')
        
        return context