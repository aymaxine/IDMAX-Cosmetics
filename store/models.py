from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.urls import reverse
from django.core.validators import MinValueValidator, MaxValueValidator
import json
from django.conf import settings
from decimal import Decimal
import os


class Category(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)

    class Meta:
        verbose_name_plural = 'Categories'

    def __str__(self):
        return self.name


class Product(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products')
    image = models.FileField(upload_to='product_images', blank=True, null=True)
    # Keep the original field for backwards compatibility
    image_path = models.CharField(max_length=255, blank=True, null=True)
    stock = models.PositiveIntegerField(default=0)
    available = models.BooleanField(default=True)
    featured = models.BooleanField(default=False)  # Mark products for carousel
    is_premium = models.BooleanField(default=False)  # New field to mark premium/exclusive products
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)  # Discount percentage for exclusive deals
    has_free_shipping = models.BooleanField(default=False)  # Free shipping exclusive feature
    limited_edition = models.BooleanField(default=False)  # Limited edition exclusive feature
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Fields for open data import
    external_id = models.CharField(max_length=100, blank=True, null=True)
    data_source = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('store:product_detail', args=[self.id])

    def get_average_rating(self):
        """Calculate the average rating for this product"""
        from django.db.models import Avg
        avg_rating = self.reviews.aggregate(Avg('rating'))['rating__avg']
        return avg_rating or 0
        
    def get_review_count(self):
        """Get the number of reviews for this product"""
        return self.reviews.count()
        
    def get_discounted_price(self):
        """Calculate the discounted price"""
        if self.discount_percentage > 0:
            discount_amount = (self.price * self.discount_percentage) / 100
            return self.price - discount_amount
        return self.price
        
    def get_exclusive_features(self):
        """Return a list of exclusive features this product has"""
        features = []
        if self.is_premium:
            features.append('premium')
        if self.limited_edition:
            features.append('limited-edition')
        if self.has_free_shipping:
            features.append('free-shipping')
        if self.discount_percentage > 0:
            features.append('discount')
        return features
        
    def save(self, *args, **kwargs):
        """Save product and update image_path for backwards compatibility"""
        super().save(*args, **kwargs)
        
        if self.image:
                

                    
            self.image_path = self.image.name
            # Save without triggering the save method again
            Product.objects.filter(pk=self.pk).update(image_path=self.image.name)


class ProductImage(models.Model):
    """Model for additional product images"""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='additional_images')
    image = models.FileField(upload_to='product_images', blank=True, null=True)
    image_url = models.CharField(max_length=255, blank=True, null=True)  # URL to the image for backward compatibility
    alt_text = models.CharField(max_length=255, blank=True)  # Alternative text for accessibility
    is_primary = models.BooleanField(default=False)  # Flag to mark the primary/featured image
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-is_primary', 'created_at']  # Primary images first, then by creation date
        
    def __str__(self):
        return f"Image for {self.product.name} ({'Primary' if self.is_primary else 'Secondary'})"
        



class Order(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    )
    PAYMENT_CHOICES = (
        ('credit_card', 'Credit Card'),
        ('paypal', 'PayPal'),
        ('bank_transfer', 'Bank Transfer'),
        ('cash_on_delivery', 'Cash On Delivery'),
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField()
    address = models.CharField(max_length=250)
    postal_code = models.CharField(max_length=20)
    city = models.CharField(max_length=100)
    country = models.CharField(max_length=100, blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    payment_method = models.CharField(max_length=30, choices=PAYMENT_CHOICES, default='credit_card')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    coupon = models.ForeignKey('Coupon', on_delete=models.SET_NULL, related_name='orders', null=True, blank=True)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    subtotal_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'Order {self.id}'

    def get_subtotal(self):
        """Calculate the order subtotal (before discount)"""
        return sum(item.get_cost() for item in self.items.all())

    def get_total_cost(self):
        """Calculate the final total (after discount)"""
        subtotal = self.get_subtotal()
        if self.coupon:
            return subtotal - self.discount_amount
        return subtotal

    def update_totals(self):
        """Update the order totals based on current items"""
        self.subtotal_price = self.get_subtotal()
        
        # Recalculate discount if coupon exists
        if self.coupon and self.coupon.is_valid():
            self.discount_amount = self.coupon.get_discount_amount(self.subtotal_price)
        else:
            self.discount_amount = 0
            
        self.total_price = self.subtotal_price - self.discount_amount
        self.save()

    def apply_coupon(self, coupon):
        """Apply a coupon to the order and calculate the discount"""
        if coupon and coupon.is_valid():
            subtotal = self.get_subtotal()
            discount = coupon.get_discount_amount(subtotal)

            self.coupon = coupon
            self.discount_amount = discount
            self.subtotal_price = subtotal
            self.total_price = subtotal - discount

            # Increment coupon usage counter
            coupon.current_uses += 1
            coupon.save()

            # Record the coupon use
            CouponUse.objects.create(
                coupon=coupon,
                user=self.user,
                order=self,
                discount_amount=discount
            )

            return True
        return False

    def get_absolute_url(self):
        return reverse('store:order_detail', args=[self.id])

    def save(self, *args, **kwargs):
        """Override save to ensure totals are always current"""
        # If this is a new order (no ID yet), just save it first
        if not self.id:
            super().save(*args, **kwargs)
            return
            
        # For existing orders, update the totals before saving
        self.subtotal_price = self.get_subtotal()
        
        # Recalculate discount if coupon exists
        if self.coupon and self.coupon.is_valid():
            self.discount_amount = self.coupon.get_discount_amount(self.subtotal_price)
            
        self.total_price = self.subtotal_price - self.discount_amount
        super().save(*args, **kwargs)


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='order_items')
    price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f'{self.id}'

    def get_cost(self):
        return self.price * self.quantity


class Cart(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='cart', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    session_id = models.CharField(max_length=100, null=True, blank=True)

    def __str__(self):
        return f'Cart {self.id}'

    def get_total_price(self):
        return sum(item.get_price() for item in self.items.all())

    def get_total_items(self):
        return sum(item.quantity for item in self.items.all())


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f'{self.product.name} - {self.quantity}'

    def get_price(self):
        return self.product.price * self.quantity


class ProductHistory(models.Model):
    """Model to store product history before edits"""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='history')
    data = models.TextField()  # JSON serialized product data
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Product histories'

    def __str__(self):
        return f'History for {self.product.name} at {self.created_at}'

    @property
    def product_data(self):
        """Return the deserialized product data"""
        return json.loads(self.data)

    @classmethod
    def create_from_product(cls, product):
        """Create a history record from a product instance"""
        product_data = {
            'name': product.name,
            'description': product.description,
            'price': str(product.price),  # Convert Decimal to string for JSON
            'category_id': product.category_id,
            'category_name': product.category.name if product.category else None,
            'image': product.image,
            'stock': product.stock,
            'available': product.available,
            'created_at': product.created_at.isoformat(),
            'updated_at': product.updated_at.isoformat(),
        }
        return cls.objects.create(
            product=product,
            data=json.dumps(product_data)
        )


class Review(models.Model):
    """Model for product reviews and ratings"""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reviews')
    rating = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Rating from 1 to 5 stars"
    )
    title = models.CharField(max_length=100)
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        # Ensure a user can only review a product once
        unique_together = ('product', 'user')

    def __str__(self):
        return f'{self.user.username} - {self.product.name} - {self.rating} stars'


class Wishlist(models.Model):
    """Model for user wishlists"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='wishlist')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'Wishlist of {self.user.username}'

    def get_total_items(self):
        return self.items.count()


class WishlistItem(models.Model):
    """Model for items in a wishlist"""
    wishlist = models.ForeignKey(Wishlist, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # Ensure a product can only be in a wishlist once
        unique_together = ('wishlist', 'product')

    def __str__(self):
        return f'{self.product.name} in {self.wishlist}'


class RecentlyViewedProduct(models.Model):
    """Model for tracking recently viewed products by users"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='recently_viewed')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    viewed_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-viewed_at']
        # Ensure a product is only in the recently viewed list once per user
        unique_together = ('user', 'product')

    def __str__(self):
        return f'{self.product.name} viewed by {self.user.username}'

    @classmethod
    def add_product_view(cls, user, product, max_items=10):
        """
        Add a product to the user's recently viewed list
        If the product is already in the list, update the timestamp
        If the list exceeds max_items, remove the oldest item
        """
        if user.is_authenticated:
            # Get or create the recently viewed item
            viewed_item, created = cls.objects.get_or_create(
                user=user,
                product=product
            )

            # If not created, update the timestamp
            if not created:
                viewed_item.save()  # This will update the auto_now field

            # Check if we need to remove old items
            user_viewed_items = cls.objects.filter(user=user)
            if user_viewed_items.count() > max_items:
                # Get the oldest items to remove
                items_to_remove = user_viewed_items.order_by('-viewed_at')[max_items:]
                for item in items_to_remove:
                    item.delete()

    @classmethod
    def get_recently_viewed(cls, user, limit=5):
        """Get the user's recently viewed products"""
        if user.is_authenticated:
            return cls.objects.filter(user=user).order_by('-viewed_at')[:limit]
        return []


class Coupon(models.Model):
    """Model for discount coupons"""
    DISCOUNT_TYPE_CHOICES = (
        ('percentage', 'Percentage'),
        ('fixed', 'Fixed Amount'),
    )

    code = models.CharField(max_length=50, unique=True)
    valid_from = models.DateTimeField()
    valid_to = models.DateTimeField()
    discount_type = models.CharField(max_length=10, choices=DISCOUNT_TYPE_CHOICES, default='percentage')
    discount_value = models.DecimalField(max_digits=5, decimal_places=2)
    active = models.BooleanField(default=True)
    max_uses = models.PositiveIntegerField(default=0, help_text="0 means unlimited")
    current_uses = models.PositiveIntegerField(default=0)
    min_order_value = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.code} - {self.discount_value}{"%" if self.discount_type == "percentage" else ""}'

    def is_valid(self):
        """Check if coupon is valid based on dates and usage"""
        now = timezone.now()
        if not self.active:
            return False
        if now < self.valid_from or now > self.valid_to:
            return False
        if self.max_uses > 0 and self.current_uses >= self.max_uses:
            return False
        return True

    def get_discount_amount(self, order_total):
        """Calculate discount amount based on order total and discount type"""
        if not self.is_valid() or order_total < self.min_order_value:
            return Decimal('0.00')

        if self.discount_type == 'percentage':
            return (order_total * self.discount_value / 100).quantize(Decimal('0.01'))
        else:  # fixed amount
            return min(self.discount_value, order_total)  # Don't discount more than the order total


class CouponUse(models.Model):
    """Model to track coupon usage by users"""
    coupon = models.ForeignKey(Coupon, on_delete=models.CASCADE, related_name='uses')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='coupon_uses')
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='coupon_uses', null=True, blank=True)
    used_at = models.DateTimeField(auto_now_add=True)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        unique_together = ('coupon', 'order')
        ordering = ['-used_at']

    def __str__(self):
        return f'{self.coupon.code} used by {self.user.username} on {self.used_at}'


class ComparisonList(models.Model):
    """Model for product comparison lists"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='comparison_list', null=True, blank=True)
    session_id = models.CharField(max_length=100, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        if self.user:
            return f'Comparison list for {self.user.username}'
        return f'Comparison list for session {self.session_id}'

    def get_products_count(self):
        """Get the number of products in the comparison list"""
        return self.products.count()

    def clear(self):
        """Remove all products from the comparison list"""
        self.products.all().delete()


class ComparisonItem(models.Model):
    """Model for items in a comparison list"""
    comparison_list = models.ForeignKey(ComparisonList, on_delete=models.CASCADE, related_name='products')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('comparison_list', 'product')
        ordering = ['-added_at']

    def __str__(self):
        return f'{self.product.name} in comparison list'