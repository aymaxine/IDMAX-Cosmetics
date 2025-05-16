from django.contrib import admin
from .models import Category, Product, Order, OrderItem, Cart, CartItem, ProductHistory, ProductImage


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name']
    search_fields = ['name']


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    raw_id_fields = ['product']
    extra = 0


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'price', 'category', 'stock', 'available', 'created_at']
    list_filter = ['available', 'created_at', 'category']
    list_editable = ['price', 'stock', 'available']
    search_fields = ['name', 'description']
    prepopulated_fields = {'name': ('name',)}
    date_hierarchy = 'created_at'
    ordering = ['name']

    def save_model(self, request, obj, form, change):
        """Override save_model to create history record before saving changes"""
        if change:  # Only create history if this is an edit, not a new product
            # Get the original object from the database
            original_obj = Product.objects.get(pk=obj.pk)
            # Create history record
            ProductHistory.create_from_product(original_obj)
        super().save_model(request, obj, form, change)

class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 3  # Show 3 empty forms for adding images
    fields = ['image', 'alt_text', 'is_primary']
    


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'first_name', 'last_name', 'email', 'status', 'total_price', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['first_name', 'last_name', 'email']
    date_hierarchy = 'created_at'
    inlines = [OrderItemInline]


class CartItemInline(admin.TabularInline):
    model = CartItem
    raw_id_fields = ['product']
    extra = 0


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'created_at']
    list_filter = ['created_at']
    search_fields = ['user__username']
    date_hierarchy = 'created_at'
    inlines = [CartItemInline]


@admin.register(ProductHistory)
class ProductHistoryAdmin(admin.ModelAdmin):
    list_display = ['product', 'created_at']
    list_filter = ['created_at']
    search_fields = ['product__name']
    date_hierarchy = 'created_at'
    readonly_fields = ['product', 'data', 'created_at']

    def has_add_permission(self, request):
        return False  # Prevent manual creation of history records
