from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from .models import Category, Product, Order, OrderItem, Cart, CartItem, Wishlist, WishlistItem
from decimal import Decimal


class CategoryModelTest(TestCase):
    """Tests for the Category model"""

    def setUp(self):
        self.category = Category.objects.create(name='Test Category')

    def test_category_creation(self):
        self.assertEqual(self.category.name, 'Test Category')
        self.assertEqual(str(self.category), 'Test Category')


class ProductModelTest(TestCase):
    """Tests for the Product model"""

    def setUp(self):
        self.category = Category.objects.create(name='Test Category')
        self.product = Product.objects.create(
            name='Test Product',
            description='Test Description',
            price=Decimal('10.00'),
            category=self.category,
            stock=10,
            available=True
        )

    def test_product_creation(self):
        self.assertEqual(self.product.name, 'Test Product')
        self.assertEqual(self.product.description, 'Test Description')
        self.assertEqual(self.product.price, Decimal('10.00'))
        self.assertEqual(self.product.category, self.category)
        self.assertEqual(self.product.stock, 10)
        self.assertTrue(self.product.available)
        self.assertEqual(str(self.product), 'Test Product')

    def test_get_absolute_url(self):
        url = self.product.get_absolute_url()
        self.assertEqual(url, reverse('store:product_detail', args=[self.product.id]))


class CartModelTest(TestCase):
    """Tests for the Cart and CartItem models"""

    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.category = Category.objects.create(name='Test Category')
        self.product = Product.objects.create(
            name='Test Product',
            description='Test Description',
            price=Decimal('10.00'),
            category=self.category,
            stock=10,
            available=True
        )
        self.cart = Cart.objects.create(user=self.user)
        self.cart_item = CartItem.objects.create(
            cart=self.cart,
            product=self.product,
            quantity=2
        )

    def test_cart_creation(self):
        self.assertEqual(self.cart.user, self.user)
        self.assertEqual(str(self.cart), f'Cart {self.cart.id}')

    def test_cart_item_creation(self):
        self.assertEqual(self.cart_item.cart, self.cart)
        self.assertEqual(self.cart_item.product, self.product)
        self.assertEqual(self.cart_item.quantity, 2)
        self.assertEqual(str(self.cart_item), 'Test Product - 2')

    def test_cart_item_get_price(self):
        self.assertEqual(self.cart_item.get_price(), Decimal('20.00'))

    def test_cart_get_total_price(self):
        self.assertEqual(self.cart.get_total_price(), Decimal('20.00'))

    def test_cart_get_total_items(self):
        self.assertEqual(self.cart.get_total_items(), 2)


class OrderModelTest(TestCase):
    """Tests for the Order and OrderItem models"""

    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.category = Category.objects.create(name='Test Category')
        self.product = Product.objects.create(
            name='Test Product',
            description='Test Description',
            price=Decimal('10.00'),
            category=self.category,
            stock=10,
            available=True
        )
        self.order = Order.objects.create(
            user=self.user,
            first_name='Test',
            last_name='User',
            email='test@example.com',
            address='Test Address',
            postal_code='12345',
            city='Test City',
            status='pending',
            total_price=Decimal('20.00')
        )
        self.order_item = OrderItem.objects.create(
            order=self.order,
            product=self.product,
            price=Decimal('10.00'),
            quantity=2
        )

    def test_order_creation(self):
        self.assertEqual(self.order.user, self.user)
        self.assertEqual(self.order.first_name, 'Test')
        self.assertEqual(self.order.last_name, 'User')
        self.assertEqual(self.order.email, 'test@example.com')
        self.assertEqual(self.order.address, 'Test Address')
        self.assertEqual(self.order.postal_code, '12345')
        self.assertEqual(self.order.city, 'Test City')
        self.assertEqual(self.order.status, 'pending')
        self.assertEqual(self.order.total_price, Decimal('20.00'))
        self.assertEqual(str(self.order), f'Order {self.order.id}')

    def test_order_item_creation(self):
        self.assertEqual(self.order_item.order, self.order)
        self.assertEqual(self.order_item.product, self.product)
        self.assertEqual(self.order_item.price, Decimal('10.00'))
        self.assertEqual(self.order_item.quantity, 2)
        self.assertEqual(str(self.order_item), f'{self.order_item.id}')

    def test_order_item_get_cost(self):
        self.assertEqual(self.order_item.get_cost(), Decimal('20.00'))

    def test_order_get_total_cost(self):
        self.assertEqual(self.order.get_total_cost(), Decimal('20.00'))


class ViewsTest(TestCase):
    """Tests for the views"""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.admin_user = User.objects.create_user(
            username='admin', 
            password='adminpass',
            is_staff=True,
            is_superuser=True
        )
        self.category = Category.objects.create(name='Test Category')
        self.product = Product.objects.create(
            name='Test Product',
            description='Test Description',
            price=Decimal('10.00'),
            category=self.category,
            stock=10,
            available=True
        )

    def test_home_view(self):
        response = self.client.get(reverse('store:home'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'store/home.html')
        self.assertIn('categories', response.context)
        self.assertIn('featured_products', response.context)

    def test_product_list_view(self):
        response = self.client.get(reverse('store:product_list'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'store/product_list.html')
        self.assertIn('products', response.context)
        self.assertIn('categories', response.context)

    def test_product_detail_view(self):
        response = self.client.get(reverse('store:product_detail', args=[self.product.id]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'store/product_detail.html')
        self.assertEqual(response.context['product'], self.product)
        self.assertIn('cart_product_form', response.context)

    def test_cart_add_view(self):
        # Test adding to cart as anonymous user - should redirect to login
        response = self.client.post(reverse('store:cart_add', args=[self.product.id]))
        self.assertRedirects(response, f"{reverse('login')}?next={reverse('store:cart_add', args=[self.product.id])}")

        # Test adding to cart as logged in user - should work
        self.client.login(username='testuser', password='testpass')
        response = self.client.post(reverse('store:cart_add', args=[self.product.id]))
        self.assertRedirects(response, reverse('store:cart_detail'))

    def test_cart_remove_view_requires_login(self):
        # Test removing from cart as anonymous user - should redirect to login
        response = self.client.post(reverse('store:cart_remove', args=[self.product.id]))
        self.assertRedirects(response, f"{reverse('login')}?next={reverse('store:cart_remove', args=[self.product.id])}")

        # Test removing from cart as logged in user - should work
        self.client.login(username='testuser', password='testpass')
        # First add a product to cart
        self.client.post(reverse('store:cart_add', args=[self.product.id]))
        # Then remove it
        response = self.client.post(reverse('store:cart_remove', args=[self.product.id]))
        self.assertRedirects(response, reverse('store:cart_detail'))

    def test_cart_detail_view_requires_login(self):
        # Test viewing cart as anonymous user - should redirect to login
        response = self.client.get(reverse('store:cart_detail'))
        self.assertRedirects(response, f"{reverse('login')}?next={reverse('store:cart_detail')}")

        # Test viewing cart as logged in user - should work
        self.client.login(username='testuser', password='testpass')
        response = self.client.get(reverse('store:cart_detail'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'store/cart_detail.html')

    def test_order_list_view_requires_login(self):
        # Test without login
        response = self.client.get(reverse('store:order_list'))
        self.assertRedirects(response, f"{reverse('login')}?next={reverse('store:order_list')}")

        # Test with login
        self.client.login(username='testuser', password='testpass')
        response = self.client.get(reverse('store:order_list'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'store/order_list.html')

    def test_admin_views_require_staff(self):
        # Test without login
        response = self.client.get(reverse('store:admin_dashboard'))
        self.assertRedirects(response, f"{reverse('login')}?next={reverse('store:admin_dashboard')}")

        # Test with regular user
        self.client.login(username='testuser', password='testpass')
        response = self.client.get(reverse('store:admin_dashboard'))
        self.assertEqual(response.status_code, 403)  # Forbidden

        # Test with admin user
        self.client.login(username='admin', password='adminpass')
        response = self.client.get(reverse('store:admin_dashboard'))
        self.assertEqual(response.status_code, 200)

    def test_wishlist_add_view(self):
        # Test adding to wishlist as anonymous user - should redirect to login
        response = self.client.get(reverse('store:wishlist_add', args=[self.product.id]))
        self.assertRedirects(response, f"{reverse('login')}?next={reverse('store:wishlist_add', args=[self.product.id])}")

        # Test adding to wishlist as logged in user - should work
        self.client.login(username='testuser', password='testpass')
        response = self.client.get(reverse('store:wishlist_add', args=[self.product.id]))
        self.assertRedirects(response, reverse('store:wishlist_detail'))

        # Verify product was added to wishlist
        wishlist = Wishlist.objects.get(user=self.user)
        self.assertEqual(wishlist.items.count(), 1)
        self.assertEqual(wishlist.items.first().product, self.product)

        # Test adding the same product again - should not cause an error
        response = self.client.get(reverse('store:wishlist_add', args=[self.product.id]))
        self.assertRedirects(response, reverse('store:wishlist_detail'))

        # Verify wishlist still has only one instance of the product
        wishlist = Wishlist.objects.get(user=self.user)
        self.assertEqual(wishlist.items.count(), 1)

    def test_wishlist_detail_view_requires_login(self):
        # Test viewing wishlist as anonymous user - should redirect to login
        response = self.client.get(reverse('store:wishlist_detail'))
        self.assertRedirects(response, f"{reverse('login')}?next={reverse('store:wishlist_detail')}")

        # Test viewing wishlist as logged in user - should work
        self.client.login(username='testuser', password='testpass')
        response = self.client.get(reverse('store:wishlist_detail'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'store/wishlist_detail.html')

    def test_wishlist_remove_view(self):
        # Login and add a product to wishlist first
        self.client.login(username='testuser', password='testpass')
        self.client.get(reverse('store:wishlist_add', args=[self.product.id]))

        # Test removing from wishlist
        response = self.client.get(reverse('store:wishlist_remove', args=[self.product.id]))
        self.assertRedirects(response, reverse('store:wishlist_detail'))

        # Verify product was removed from wishlist
        wishlist = Wishlist.objects.get(user=self.user)
        self.assertEqual(wishlist.items.count(), 0)
# tests.py
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from .models import Product, Review

class DeleteReviewTestCase(TestCase):
    def setUp(self):
        # Create test user and product
        self.user = User.objects.create_user(username='testuser', password='password')
        self.other_user = User.objects.create_user(username='otheruser', password='password')
        self.product = Product.objects.create(name='Test Product', price=10.0, stock=5)

        # Create a review
        self.review = Review.objects.create(
            product=self.product,
            user=self.user,
            rating=5,
            title='Great Product',
            comment='Loved it!'
        )
        self.delete_url = reverse('store:delete_review', args=[self.review.id])

    # tests.py
    from django.test import TestCase
    from django.urls import reverse
    from django.contrib.auth.models import User
    from django.contrib.messages import get_messages
    from .models import Product, Review

    class DeleteReviewFeedbackTestCase(TestCase):
        def setUp(self):
            # Create test user and product
            self.user = User.objects.create_user(username='testuser', password='password')
            self.product = Product.objects.create(name='Test Product', price=10.0, stock=5)

            # Create a review
            self.review = Review.objects.create(
                product=self.product,
                user=self.user,
                rating=5,
                title='Great Product',
                comment='Loved it!'
            )
            self.delete_url = reverse('store:delete_review', args=[self.review.id])

        def test_success_message_on_delete(self):
            # Log in as the review owner
            self.client.login(username='testuser', password='password')

            # Send POST request to delete the review
            response = self.client.post(self.delete_url)

            # Check for success message
            messages = list(get_messages(response.wsgi_request))
            self.assertEqual(len(messages), 1)
            self.assertEqual(str(messages[0]), "Review deleted successfully.")

        def test_error_message_for_nonexistent_review(self):
            # Log in as the review owner
            self.client.login(username='testuser', password='password')

            # Send POST request to delete a non-existent review
            invalid_url = reverse('store:delete_review', args=[999])
            response = self.client.post(invalid_url)

            # Check for error message
            messages = list(get_messages(response.wsgi_request))
            self.assertEqual(len(messages), 1)
            self.assertEqual(str(messages[0]), "Review not found.")