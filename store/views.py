from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, TemplateView
from django.db.models import Q, Sum, Count, F
from django.db import models, transaction
from django.urls import reverse
from django.http import JsonResponse, HttpResponseRedirect
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.utils import timezone
from django.contrib.auth.models import User
from .models import (
  Category, Product, Order, OrderItem, Cart, CartItem, Review,
  Wishlist, WishlistItem, Coupon, CouponUse, ComparisonList, ComparisonItem
)
from .forms import OrderCreateForm, CartAddProductForm, ReviewForm, CouponApplyForm
import json
import logging
from decimal import Decimal


# Custom error handlers
def handler404(request, exception):
  """Custom 404 error handler"""
  return render(request, 'store/404.html', status=404)


# About and Contact pages
def about(request):
  """About page view"""
  return render(request, 'store/about.html')


def contact(request):
  """Contact page view"""
  return render(request, 'store/contact.html')


# Set up logging
logger = logging.getLogger(__name__)


def home(request):
  """Home page view with featured products, categories, and recently viewed products"""
  categories = Category.objects.all()[:6]
  
  # Get featured products for the carousel
  carousel_products = Product.objects.filter(available=True, featured=True)[:5]
  
  # Get other featured products (that aren't in the carousel) for the regular display
  featured_products = Product.objects.filter(available=True).order_by('-created_at')[:8]

  context = {
    'categories': categories,
    'featured_products': featured_products,
    'carousel_products': carousel_products,
    'title': 'Home'
  }

  # Add recently viewed products if user is authenticated
  if request.user.is_authenticated:
    from .models import RecentlyViewedProduct
    recently_viewed = RecentlyViewedProduct.get_recently_viewed(request.user)
    recently_viewed_products = [item.product for item in recently_viewed][:4]
    context['recently_viewed_products'] = recently_viewed_products

  return render(request, 'store/home.html', context)


def category_redirect(request, category_id):
  """Redirect from /products/category=X to /products/?category=X"""
  url = f"{reverse('store:product_list')}?category={category_id}"
  return HttpResponseRedirect(url)


def sort_redirect(request, sort_option):
  """Redirect from /products/sort=X to /products/?sort=X"""
  url = f"{reverse('store:product_list')}?sort={sort_option}"
  return HttpResponseRedirect(url)


class ProductListView(ListView):
  """List view for all products with pagination and filtering"""
  model = Product
  template_name = 'store/product_list.html'
  context_object_name = 'products'
  paginate_by = 24

  def get_paginate_by(self, queryset):
    # Check if 'show_all' parameter is present
    show_all = self.request.GET.get('show_all')
    if show_all:
      return None  # Return None to disable pagination
    return self.paginate_by

  def get_queryset(self):
    queryset = Product.objects.filter(available=True)

    # Filter by category if provided
    category_id = self.request.GET.get('category')
    if category_id:
      queryset = queryset.filter(category_id=category_id)

    # Filter by search query if provided
    query = self.request.GET.get('q')
    if query:
      queryset = queryset.filter(
        Q(name__icontains=query) |
        Q(description__icontains=query) |
        Q(category__name__icontains=query)
      )
    
    # Filter by exclusive features
    if self.request.GET.get('premium') == 'true':
      queryset = queryset.filter(is_premium=True)
      
    if self.request.GET.get('discount') == 'true':
      queryset = queryset.filter(discount_percentage__gt=0)
      
    if self.request.GET.get('free_shipping') == 'true':
      queryset = queryset.filter(has_free_shipping=True)
      
    if self.request.GET.get('limited_edition') == 'true':
      queryset = queryset.filter(limited_edition=True)

    # Sort products
    sort = self.request.GET.get('sort', 'name')
    if sort == 'price_asc':
      queryset = queryset.order_by('price')
    elif sort == 'price_desc':
      queryset = queryset.order_by('-price')
    elif sort == 'newest':
      queryset = queryset.order_by('-created_at')
    else:
      queryset = queryset.order_by('name')

    return queryset

  def get_context_data(self, **kwargs):
    context = super().get_context_data(**kwargs)
    context['categories'] = Category.objects.all()
    context['category_id'] = self.request.GET.get('category', '')
    context['query'] = self.request.GET.get('q', '')
    context['sort'] = self.request.GET.get('sort', 'name')
    context['show_all'] = self.request.GET.get('show_all', '')

    # Add total product count
    context['total_products'] = Product.objects.filter(available=True).count()

    return context


class ProductDetailView(DetailView):
  """Detail view for a single product"""
  model = Product
  template_name = 'store/product_detail.html'

  def get_context_data(self, **kwargs):
    context = super().get_context_data(**kwargs)
    context['cart_product_form'] = CartAddProductForm()

    # Add review form and reviews to context
    context['review_form'] = ReviewForm()
    reviews = self.object.reviews.all()
    context['reviews'] = reviews

    # Check if the current user has already reviewed this product
    if self.request.user.is_authenticated:
      context['user_has_reviewed'] = Review.objects.filter(
        product=self.object,
        user=self.request.user
      ).exists()
    else:
      context['user_has_reviewed'] = False

    # Calculate rating statistics
    rating_stats = self._calculate_rating_stats(reviews)
    context.update(rating_stats)
    
    # Get additional product images
    additional_images = self.object.additional_images.all()
    context['additional_images'] = additional_images
    
    # Get exclusive features
    context['exclusive_features'] = self.object.get_exclusive_features()

    # Get related products from the same category if category exists
    if self.object.category:
      context['related_products'] = Product.objects.filter(
        category=self.object.category
      ).exclude(id=self.object.id)[:4]
    else:
      context['related_products'] = Product.objects.filter(
        available=True
      ).exclude(id=self.object.id)[:4]

    # Get the most recent history record for this product
    try:
      history = self.object.history.first()
      if history:
        context['previous_version'] = history.product_data
    except Exception as e:
      logger.error(f"Error retrieving product history: {e}")

    # Get recently viewed products for the user (excluding current product)
    if self.request.user.is_authenticated:
      from .models import RecentlyViewedProduct
      recently_viewed = RecentlyViewedProduct.get_recently_viewed(self.request.user)
      # Convert to list of products and exclude current product
      recently_viewed_products = [item.product for item in recently_viewed if item.product.id != self.object.id][:4]
      context['recently_viewed_products'] = recently_viewed_products

    return context

  def _calculate_rating_stats(self, reviews):
    """Calculate detailed rating statistics for a product"""
    from django.db.models import Avg, Count, Case, When, IntegerField

    stats = {
      'rating_count': reviews.count(),
      'rating_avg': 0,
      'rating_distribution': {1: 0, 2: 0, 3: 0, 4: 0, 5: 0},
      'rating_percentage': {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    }

    if stats['rating_count'] > 0:
      # Use aggregation to calculate average rating
      avg_rating = reviews.aggregate(Avg('rating'))['rating__avg']
      stats['rating_avg'] = avg_rating or 0

      # Use aggregation to count ratings by value
      rating_counts = reviews.aggregate(
        r1=Count(Case(When(rating=1, then=1), output_field=IntegerField())),
        r2=Count(Case(When(rating=2, then=1), output_field=IntegerField())),
        r3=Count(Case(When(rating=3, then=1), output_field=IntegerField())),
        r4=Count(Case(When(rating=4, then=1), output_field=IntegerField())),
        r5=Count(Case(When(rating=5, then=1), output_field=IntegerField()))
      )

      # Update distribution dictionary
      stats['rating_distribution'] = {
        1: rating_counts['r1'],
        2: rating_counts['r2'],
        3: rating_counts['r3'],
        4: rating_counts['r4'],
        5: rating_counts['r5']
      }

      # Calculate percentage for each rating
      for rating in range(1, 6):
        stats['rating_percentage'][rating] = (stats['rating_distribution'][rating] / stats['rating_count']) * 100

    return stats

  def get(self, request, *args, **kwargs):
    response = super().get(request, *args, **kwargs)

    # Track this product view in recently viewed products
    if request.user.is_authenticated:
      from .models import RecentlyViewedProduct
      RecentlyViewedProduct.add_product_view(request.user, self.object)

    return response


@login_required
def cart_add(request, product_id):
  """Add a product to the cart"""
  # Check if we're adding all items from wishlist
  add_all_from_wishlist = request.POST.get('add_all_from_wishlist')

  if add_all_from_wishlist:
    try:
      # Get the user's wishlist
      wishlist = get_object_or_404(Wishlist, user=request.user)
      wishlist_items = wishlist.items.all()

      if not wishlist_items:
        messages.warning(request, "Your wishlist is empty.")
        return redirect('store:wishlist_detail')

      # Get or create cart
      cart, created = Cart.objects.get_or_create(user=request.user)

      # Add each wishlist item to cart
      added_count = 0
      for wishlist_item in wishlist_items:
        cart_item, item_created = CartItem.objects.get_or_create(
          cart=cart,
          product=wishlist_item.product,
          defaults={'quantity': 0}
        )

        # If item already in cart, increment quantity by 1
        cart_item.quantity += 1
        cart_item.save()
        added_count += 1

      messages.success(request, f'{added_count} items added to your cart from your wishlist.')
      return redirect('store:cart_detail')

    except Exception as e:
      logger.error(f"Error adding wishlist items to cart: {e}")
      messages.error(request, "There was an error adding wishlist items to your cart.")
      return redirect('store:wishlist_detail')

  # Regular add to cart functionality
  product = get_object_or_404(Product, id=product_id)

  try:
    # Get or create cart
    cart, created = Cart.objects.get_or_create(user=request.user)

    # Get or create cart item
    cart_item, item_created = CartItem.objects.get_or_create(
      cart=cart,
      product=product,
      defaults={'quantity': 0}
    )

    # Update quantity
    if request.method == 'POST':
      form = CartAddProductForm(request.POST)
      if form.is_valid():
        cd = form.cleaned_data
        cart_item.quantity = cd['quantity']
        cart_item.save()
        messages.success(request, f'{product.name} added to your cart.')
    else:
      # If GET request, just add 1
      cart_item.quantity += 1
      cart_item.save()
      messages.success(request, f'{product.name} added to your cart.')

  except Exception as e:
    logger.error(f"Error adding product to cart: {e}")
    messages.error(request, "There was an error adding the product to your cart.")

  return redirect('store:cart_detail')


@login_required
def cart_remove(request, product_id):
  """Remove a product from the cart"""
  product = get_object_or_404(Product, id=product_id)

  try:
    cart = get_object_or_404(Cart, user=request.user)

    cart_item = get_object_or_404(CartItem, cart=cart, product=product)
    cart_item.delete()
    messages.success(request, f'{product.name} removed from your cart.')
  except Exception as e:
    logger.error(f"Error removing product from cart: {e}")
    messages.error(request, "There was an error removing the product from your cart.")

  return redirect('store:cart_detail')


@login_required
def cart_detail(request):
  """Display the cart contents"""
  try:
    cart, created = Cart.objects.get_or_create(user=request.user)
    cart_items = cart.items.all()
  except Exception as e:
    logger.error(f"Error retrieving cart: {e}")
    cart_items = []
    messages.error(request, "There was an error retrieving your cart.")

  return render(request, 'store/cart_detail.html', {'cart_items': cart_items})


@login_required
def coupon_apply(request):
  """Apply or remove a coupon from the current session"""
  if request.method == 'POST':
    code = request.POST.get('code')

    # Handle coupon removal
    if code == 'remove':
      if 'coupon_id' in request.session:
        del request.session['coupon_id']
        messages.success(request, "Coupon removed successfully.")
      return redirect('store:order_create')

    # Handle coupon application
    form = CouponApplyForm(request.POST)
    if form.is_valid():
      code = form.cleaned_data['code']
      try:
        coupon = Coupon.objects.get(code__iexact=code, active=True)

        # Verify coupon is valid
        if coupon.is_valid():
          # Store coupon in session
          request.session['coupon_id'] = coupon.id
          messages.success(request, f"Coupon '{coupon.code}' applied successfully!")
        else:
          messages.error(request, "This coupon is no longer valid.")
      except Coupon.DoesNotExist:
        request.session['coupon_id'] = None
        messages.error(request, "Invalid coupon code.")
    else:
      for field, errors in form.errors.items():
        for error in errors:
          messages.error(request, error)

  # Redirect back to the checkout page
  return redirect('store:order_create')


@login_required
def order_create(request):
  """Create a new order"""
  try:
    cart, created = Cart.objects.get_or_create(user=request.user)
    cart_items = cart.items.all()

    if not cart_items:
      messages.warning(request, "Your cart is empty. Please add some products before checkout.")
      return redirect('store:product_list')

    # Get coupon from session if exists
    coupon = None
    coupon_id = request.session.get('coupon_id')
    if coupon_id:
      try:
        coupon = Coupon.objects.get(id=coupon_id, active=True)
        if not coupon.is_valid():
          messages.warning(request, "The coupon is no longer valid and has been removed.")
          coupon = None
          request.session['coupon_id'] = None
      except Coupon.DoesNotExist:
        coupon = None
        request.session['coupon_id'] = None

    # Calculate cart total
    cart_total = sum(item.get_price() for item in cart_items)

    # Calculate discount if coupon exists
    discount = Decimal('0.00')
    if coupon:
      discount = coupon.get_discount_amount(cart_total)

    # Final total after discount
    total_after_discount = cart_total - discount

    if request.method == 'POST':
      form = OrderCreateForm(request.POST)
      if form.is_valid():
        order = form.save(commit=False)
        order.user = request.user
        order.subtotal_price = cart_total
        order.total_price = total_after_discount

        # Apply coupon if exists
        if coupon:
          order.coupon = coupon
          order.discount_amount = discount

        order.save()

        for item in cart_items:
          OrderItem.objects.create(
            order=order,
            product=item.product,
            price=item.product.price,
            quantity=item.quantity
          )

        # If coupon was applied, record its use
        if coupon:
          coupon.current_uses += 1
          coupon.save()

          CouponUse.objects.create(
            coupon=coupon,
            user=request.user,
            order=order,
            discount_amount=discount
          )

          # Clear coupon from session
          request.session['coupon_id'] = None

        # Clear the cart
        cart_items.delete()

        messages.success(request, "Your order has been successfully placed!")
        return redirect('store:order_detail', order.id)
    else:
      # Pre-fill form with user information
      initial_data = {
        'first_name': request.user.first_name,
        'last_name': request.user.last_name,
        'email': request.user.email,
      }
      form = OrderCreateForm(initial=initial_data)

    # Create coupon form
    coupon_form = CouponApplyForm()

    return render(request, 'store/order_create.html', {
      'cart_items': cart_items,
      'form': form,
      'coupon_form': coupon_form,
      'cart_total': cart_total,
      'coupon': coupon,
      'discount': discount,
      'total_after_discount': total_after_discount
    })
  except Exception as e:
    logger.error(f"Error creating order: {e}")
    messages.error(request, "There was an error processing your order. Please try again.")
    return redirect('store:cart_detail')


@login_required
def order_detail(request, order_id):
  """Display order details"""
  try:
    order = get_object_or_404(Order, id=order_id, user=request.user)
    return render(request, 'store/order_detail.html', {'order': order})
  except Exception as e:
    logger.error(f"Error retrieving order: {e}")
    messages.error(request, "There was an error retrieving your order.")
    return redirect('store:order_list')


@login_required
def order_list(request):
  """Display list of user's orders"""
  try:
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'store/order_list.html', {'orders': orders})
  except Exception as e:
    logger.error(f"Error retrieving orders: {e}")
    messages.error(request, "There was an error retrieving your orders.")
    return redirect('store:home')


@login_required
def order_cancel(request, order_id):
  """Cancel a pending order"""
  if request.method == 'POST':
    try:
      with transaction.atomic():  # Added transaction atomic
        order = get_object_or_404(Order, id=order_id, user=request.user, status='pending')
        order.status = 'cancelled'
        order.save()
        messages.success(request, f"Order #{order.id} has been cancelled.")
    except Exception as e:
      logger.error(f"Error cancelling order: {e}")
      messages.error(request, "There was an error cancelling your order.")
  return redirect('store:order_list')


class AdminOrderListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
  """Admin view for all orders"""
  model = Order
  template_name = 'store/admin/order_list.html'
  context_object_name = 'orders'
  paginate_by = 20

  def test_func(self):
    return self.request.user.is_staff

  def get_queryset(self):
    queryset = Order.objects.all().order_by('-created_at')

    # Filter by status if provided
    status = self.request.GET.get('status')
    if status:
      queryset = queryset.filter(status=status)

    return queryset

  def get_context_data(self, **kwargs):
    context = super().get_context_data(**kwargs)
    context['status'] = self.request.GET.get('status', '')

    # Add statistics for dashboard
    context['total_orders'] = Order.objects.count()
    context['pending_orders'] = Order.objects.filter(status='pending').count()
    context['total_revenue'] = Order.objects.aggregate(Sum('total_price'))['total_price__sum'] or 0

    # Orders by status chart data
    status_data = Order.objects.values('status').annotate(count=Count('id'))
    context['status_data'] = json.dumps({item['status']: item['count'] for item in status_data})

    return context


class AdminOrderUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
  """Admin view to update order status"""
  model = Order
  template_name = 'store/admin/order_update.html'
  fields = ['status']

  def test_func(self):
    return self.request.user.is_staff

  def get_success_url(self):
    messages.success(self.request, f"Order #{self.object.id} has been updated.")
    return reverse('store:admin_order_list')


class AdminOrderDetailView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    """Admin view for detailed order information"""
    model = Order
    template_name = 'store/admin/order_detail.html'
    context_object_name = 'order'

    def test_func(self):
        return self.request.user.is_staff

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context


@login_required
def add_review(request, product_id):
  """Add or update a product review"""
  product = get_object_or_404(Product, id=product_id)

  # Check if user already has a review for this product
  try:
    review = Review.objects.get(product=product, user=request.user)
    # If review exists, we're updating
    is_update = True
  except Review.DoesNotExist:
    # If no review exists, we're creating a new one
    review = None
    is_update = False

  if request.method == 'POST':
    form = ReviewForm(request.POST, instance=review)
    if form.is_valid():
      review = form.save(commit=False)
      review.product = product
      review.user = request.user
      review.save()

      if is_update:
        messages.success(request, "Your review has been updated.")
      else:
        messages.success(request, "Your review has been added.")

      return redirect('store:product_detail', pk=product.id)
    else:
      messages.error(request, "There was an error with your review. Please check the form.")
  else:
    # If GET request, redirect to product detail page
    return redirect('store:product_detail', pk=product.id)

  # If form is invalid, redirect back to product detail with error message
  return redirect('store:product_detail', pk=product.id)


# Fix in delete_review view
@login_required
def delete_review(request, review_id):
  try:
    review = get_object_or_404(Review, id=review_id, user=request.user)
    product_id = review.product.id
    review.delete()
    messages.success(request, "Review deleted successfully.")
    return redirect('store:product_detail', pk=product_id)  # <-- use pk
  except Review.DoesNotExist:
    messages.error(request, "Review not found.")
    return redirect('store:product_list')
  except Exception as e:
    messages.error(request, f"An error occurred: {str(e)}")
    return redirect('store:product_list')


@login_required
@transaction.atomic
def wishlist_detail(request):
  """Display the wishlist contents"""
  try:
    wishlist, created = Wishlist.objects.get_or_create(user=request.user)
    wishlist_items = wishlist.items.all().order_by('-added_at')
  except Exception as e:
    logger.error(f"Error retrieving wishlist: {e}")
    wishlist_items = []
    messages.error(request, "There was an error retrieving your wishlist.")

  return render(request, 'store/wishlist_detail.html', {'wishlist_items': wishlist_items})


@login_required
@transaction.atomic
def wishlist_add(request, product_id):
  """Add a product to the wishlist"""
  product = get_object_or_404(Product, id=product_id)

  try:
    # Get or create wishlist within the transaction
    wishlist, created = Wishlist.objects.get_or_create(user=request.user)

    # Check if product is already in wishlist
    if WishlistItem.objects.filter(wishlist=wishlist, product=product).exists():
      messages.info(request, f'{product.name} is already in your wishlist.')
    else:
      try:
        # Add product to wishlist
        WishlistItem.objects.create(wishlist=wishlist, product=product)
        messages.success(request, f'{product.name} added to your wishlist.')
      except:
        # If creation fails due to unique constraint (product already in wishlist)
        messages.info(request, f'{product.name} is already in your wishlist.')

  except Exception as e:
    logger.error(f"Error adding product to wishlist: {e}")
    messages.error(request, "There was an error adding the product to your wishlist.")

  # Redirect back to the product page if coming from there, otherwise to wishlist
  next_url = request.GET.get('next')
  if next_url:
    return redirect(next_url)
  return redirect('store:wishlist_detail')


@login_required
@transaction.atomic
def wishlist_remove(request, product_id):
  """Remove a product from the wishlist"""
  product = get_object_or_404(Product, id=product_id)

  try:
    wishlist = get_object_or_404(Wishlist, user=request.user)
    wishlist_item = get_object_or_404(WishlistItem, wishlist=wishlist, product=product)
    wishlist_item.delete()
    messages.success(request, f'{product.name} removed from your wishlist.')
  except Exception as e:
    logger.error(f"Error removing product from wishlist: {e}")
    messages.error(request, "There was an error removing the product from your wishlist.")

  return redirect('store:wishlist_detail')


def comparison_list_detail(request):
  """Display the comparison list"""
  # Get or create comparison list
  comparison_list = None

  if request.user.is_authenticated:
    # For authenticated users, get or create their comparison list
    comparison_list, created = ComparisonList.objects.get_or_create(user=request.user)
  else:
    # For anonymous users, use session ID
    session_id = request.session.session_key
    if not session_id:
      request.session.save()
      session_id = request.session.session_key

    comparison_list, created = ComparisonList.objects.get_or_create(session_id=session_id)

  # Get comparison items
  comparison_items = comparison_list.products.all().select_related('product')
  products = [item.product for item in comparison_items]

  # Get all product attributes for comparison
  attributes = {}
  if products:
    # Basic attributes all products have
    attributes['Price'] = {p.id: f"${p.price}" for p in products}
    attributes['Category'] = {p.id: p.category.name if p.category else "Uncategorized" for p in products}
    attributes['In Stock'] = {p.id: "Yes" if p.stock > 0 else "No" for p in products}
    attributes['Stock Count'] = {p.id: p.stock for p in products}

    # Get average rating with error handling
    attributes['Rating'] = {}
    for p in products:
      try:
        rating = p.get_average_rating()
        attributes['Rating'][p.id] = f"{rating:.1f}/5.0" if rating is not None else "No ratings"
      except (AttributeError, TypeError):
        # Handle case where method doesn't exist or returns None
        attributes['Rating'][p.id] = "No ratings"

    # Get review count with error handling
    attributes['Reviews'] = {}
    for p in products:
      try:
        count = p.get_review_count()
        attributes['Reviews'][p.id] = count if count is not None else 0
      except AttributeError:
        # Handle case where method doesn't exist
        attributes['Reviews'][p.id] = 0

  return render(request, 'store/comparison_list.html', {
    'comparison_list': comparison_list,
    'products': products,
    'attributes': attributes
  })


def comparison_add(request, product_id):
  """Add a product to the comparison list"""
  product = get_object_or_404(Product, id=product_id)

  # Get or create comparison list
  comparison_list = None

  if request.user.is_authenticated:
    # For authenticated users, get or create their comparison list
    comparison_list, created = ComparisonList.objects.get_or_create(user=request.user)
  else:
    # For anonymous users, use session ID
    session_id = request.session.session_key
    if not session_id:
      request.session.save()
      session_id = request.session.session_key

    comparison_list, created = ComparisonList.objects.get_or_create(session_id=session_id)

  # Check if product is already in comparison list
  if ComparisonItem.objects.filter(comparison_list=comparison_list, product=product).exists():
    messages.info(request, f'{product.name} is already in your comparison list.')
  else:
    # Add product to comparison list
    ComparisonItem.objects.create(comparison_list=comparison_list, product=product)
    messages.success(request, f'{product.name} added to your comparison list.')

  # Redirect back to the product page if coming from there, otherwise to comparison list
  next_url = request.GET.get('next')
  if next_url:
    return redirect(next_url)
  return redirect('store:comparison_list')


def comparison_remove(request, product_id):
  """Remove a product from the comparison list"""
  product = get_object_or_404(Product, id=product_id)

  # Get comparison list
  comparison_list = None

  if request.user.is_authenticated:
    comparison_list = get_object_or_404(ComparisonList, user=request.user)
  else:
    session_id = request.session.session_key
    if session_id:
      comparison_list = get_object_or_404(ComparisonList, session_id=session_id)

  if comparison_list:
    # Remove product from comparison list
    try:
      comparison_item = get_object_or_404(ComparisonItem, comparison_list=comparison_list, product=product)
      comparison_item.delete()
      messages.success(request, f'{product.name} removed from your comparison list.')
    except:
      messages.error(request, f'Could not remove {product.name} from your comparison list.')

  return redirect('store:comparison_list')


def comparison_clear(request):
  """Clear all products from the comparison list"""
  # Get comparison list
  comparison_list = None

  if request.user.is_authenticated:
    comparison_list = get_object_or_404(ComparisonList, user=request.user)
  else:
    session_id = request.session.session_key
    if session_id:
      comparison_list = get_object_or_404(ComparisonList, session_id=session_id)

  if comparison_list:
    # Clear comparison list
    comparison_list.clear()
    messages.success(request, 'Your comparison list has been cleared.')

  return redirect('store:comparison_list')


class AdminDashboardView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
  """Admin dashboard with statistics and charts"""
  template_name = 'store/admin/dashboard.html'

  def test_func(self):
    return self.request.user.is_staff
  def get_context_data(self, **kwargs):
    context = super().get_context_data(**kwargs)
    
    # Get date 30 days ago for stats
    from datetime import timedelta
    from django.utils import timezone
    thirty_days_ago = timezone.now() - timedelta(days=30)
    seven_days_ago = timezone.now() - timedelta(days=7)

    # Basic statistics
    context['total_products'] = Product.objects.count()
    context['total_orders'] = Order.objects.count()
    context['total_users'] = User.objects.count()
    context['total_revenue'] = Order.objects.aggregate(Sum('total_price'))['total_price__sum'] or 0
    
    # User statistics
    context['new_users_month'] = User.objects.filter(date_joined__gte=thirty_days_ago).count()
    context['new_users_week'] = User.objects.filter(date_joined__gte=seven_days_ago).count()
    context['active_users'] = User.objects.filter(is_active=True).count()
    context['staff_users'] = User.objects.filter(is_staff=True).count()

    # Recent orders
    context['recent_orders'] = Order.objects.order_by('-created_at')[:5]

    # Orders by status
    status_data = Order.objects.values('status').annotate(count=Count('id'))
    context['status_data'] = json.dumps({item['status']: item['count'] for item in status_data})

    # Sales by category
    category_data = OrderItem.objects.exclude(
      product__category__isnull=True
    ).values('product__category__name').annotate(
      total=Sum(F('price') * F('quantity'), output_field=models.DecimalField())
    ).order_by('-total')[:5]

    # Add uncategorized products if any
    uncategorized_total = OrderItem.objects.filter(
      product__category__isnull=True
    ).aggregate(
      total=Sum(F('price') * F('quantity'), output_field=models.DecimalField())
    )['total'] or 0

    # Prepare data for JSON
    category_json_data = {
      item['product__category__name']: float(item['total']) for item in category_data
    }

    # Add uncategorized if there are any
    if uncategorized_total > 0:
      category_json_data['Uncategorized'] = float(uncategorized_total)

    context['category_data'] = json.dumps(category_json_data)

    return context