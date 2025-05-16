from django import forms
from django.forms import inlineformset_factory
from .models import Order, Review, Coupon, Product, Category, ProductImage


class CartAddProductForm(forms.Form):
    """Form for adding products to the cart"""
    quantity = forms.IntegerField(
        min_value=1,
        max_value=100,
        initial=1,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'style': 'width: 80px;'})
    )


class OrderCreateForm(forms.ModelForm):
    """Form for creating a new order"""
    class Meta:
        model = Order
        fields = ['first_name', 'last_name', 'email', 'address', 'postal_code', 'city', 
                 'country', 'phone', 'notes', 'payment_method']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'address': forms.TextInput(attrs={'class': 'form-control'}),
            'postal_code': forms.TextInput(attrs={'class': 'form-control'}),
            'city': forms.TextInput(attrs={'class': 'form-control'}),
            'country': forms.TextInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'payment_method': forms.Select(attrs={'class': 'form-control'}),
        }


class ProductSearchForm(forms.Form):
    """Form for searching products"""
    query = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search products...'
        })
    )
    category = forms.ChoiceField(
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    def __init__(self, *args, **kwargs):
        categories = kwargs.pop('categories', [])
        super().__init__(*args, **kwargs)

        # Add empty choice
        category_choices = [('', 'All Categories')]
        # Add categories from database
        category_choices.extend([(c.id, c.name) for c in categories])
        self.fields['category'].choices = category_choices


class ReviewForm(forms.ModelForm):
    """Form for submitting product reviews"""
    class Meta:
        model = Review
        fields = ['rating', 'title', 'comment']
        widgets = {
            'rating': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1,
                'max': 5,
                'step': 1,
                'placeholder': 'Rate from 1 to 5'
            }),
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Brief summary of your review'
            }),
            'comment': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Share your experience with this product'
            }),
        }
        labels = {
            'rating': 'Rating (1-5 stars)',
            'title': 'Review Title',
            'comment': 'Your Review'
        }
        help_texts = {
            'rating': 'Select a rating between 1 and 5 stars',
            'title': 'Give your review a title',
            'comment': 'Tell others about your experience with this product'
        }


class CouponApplyForm(forms.Form):
    """Form for applying coupon codes"""
    code = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter coupon code',
            'aria-label': 'Coupon code',
        })
    )

    def clean_code(self):
        code = self.cleaned_data.get('code')
        if code:
            try:
                coupon = Coupon.objects.get(code__iexact=code, active=True)
                if not coupon.is_valid():
                    raise forms.ValidationError("This coupon is no longer valid.")
                return code
            except Coupon.DoesNotExist:
                raise forms.ValidationError("Invalid coupon code.")
        return code


class CategoryForm(forms.ModelForm):
    """Form for creating and updating categories"""
    class Meta:
        model = Category
        fields = ['name', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class ProductForm(forms.ModelForm):
    """Form for creating and updating products"""
    class Meta:
        model = Product
        fields = [
            'name', 'description', 'price', 'category', 
            'image', 'stock', 'available', 'featured',
            'is_premium', 'discount_percentage', 'has_free_shipping',
            'limited_edition'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 5}),
            'price': forms.NumberInput(attrs={'class': 'form-control'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'image': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'stock': forms.NumberInput(attrs={'class': 'form-control'}),
            'available': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'featured': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_premium': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'discount_percentage': forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'max': '100'}),
            'has_free_shipping': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'limited_edition': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean_price(self):
        price = self.cleaned_data.get('price')
        if price and price <= 0:
            raise forms.ValidationError("Price must be greater than zero.")
        return price

    def clean_discount_percentage(self):
        discount = self.cleaned_data.get('discount_percentage')
        if discount and (discount < 0 or discount > 100):
            raise forms.ValidationError("Discount percentage must be between 0 and 100.")
        return discount


class ProductImageForm(forms.ModelForm):
    """Form for product additional images"""
    class Meta:
        model = ProductImage
        fields = ['image', 'alt_text', 'is_primary']
        widgets = {
            'image': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'alt_text': forms.TextInput(attrs={'class': 'form-control'}),
            'is_primary': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


# Create a formset for handling multiple product images
ProductImageFormSet = inlineformset_factory(
    Product, 
    ProductImage,
    form=ProductImageForm,
    extra=3,  # Number of empty forms to display
    max_num=10,  # Maximum number of forms
    can_delete=True  # Allow deleting images
)