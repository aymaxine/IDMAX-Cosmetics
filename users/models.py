from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
# from PIL import Image  # Uncommented the PIL import
import logging

logger = logging.getLogger(__name__)

class Profile(models.Model):
    """
    Extended user profile model.
    This model extends the built-in User model with additional fields.
    """
    USER_TYPE_CHOICES = (
        ('customer', 'Customer'),
        ('staff', 'Staff'),
        ('admin', 'Admin'),
    )

    COUNTRY_CHOICES = (
        ('US', 'United States'),
        ('UK', 'United Kingdom'),
        # Add more countries as needed
    )

    user = models.OneToOneField(User, on_delete=models.CASCADE, db_index=True)
    # image = models.ImageField(default='default.jpg', upload_to='profile_pics')
    image = models.CharField(max_length=255, default='default.jpg')  # Changed to CharField to avoid Pillow dependency
    phone = models.CharField(max_length=20, blank=True, null=True)
    address = models.CharField(max_length=255, blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    postal_code = models.CharField(max_length=20, blank=True, null=True)
    country = models.CharField(
        max_length=2, 
        choices=COUNTRY_CHOICES,
        blank=True,
        null=True
    )
    user_type = models.CharField(
        max_length=20,
        choices=USER_TYPE_CHOICES,
        default='customer'
    )

    def clean(self):
        """Validate model fields"""
        if self.phone and not self.phone.isdigit():
            raise ValidationError({'phone': 'Phone number must contain only digits'})

    def __str__(self):
        return f'{self.user.username} Profile'

    def save(self, *args, **kwargs):
        """Override save method to resize profile image"""
        super().save(*args, **kwargs)

        # try:
        #     if self.image:
        #         img = Image.open(self.image.path)
        #         if img.height > 300 or img.width > 300:
        #             output_size = (300, 300)
        #             img.thumbnail(output_size)
        #             img.save(self.image.path, quality=85, optimize=True)
        # except IOError as e:
        #     logger.error(f"Error processing profile image: {e}")
        # except Exception as e:
        #     logger.error(f"Unexpected error while processing profile image: {e}")
