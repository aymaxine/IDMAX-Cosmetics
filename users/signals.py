from django.db.models.signals import post_save
from django.contrib.auth.models import User
from django.dispatch import receiver
from .models import Profile
import logging

# Set up logging
logger = logging.getLogger(__name__)

@receiver(post_save, sender=User)
def create_profile(sender, instance, created, **kwargs):
    """
    Signal to create a profile when a new user is created.
    This ensures every user has a profile.
    """
    if created:
        try:
            Profile.objects.create(user=instance)
            logger.info(f"Profile created for user: {instance.username}")
        except Exception as e:
            logger.error(f"Error creating profile for user {instance.username}: {e}")


@receiver(post_save, sender=User)
def save_profile(sender, instance, **kwargs):
    """
    Signal to save a profile when a user is updated.
    This ensures the profile is always in sync with the user.
    """
    try:
        instance.profile.save()
    except Exception as e:
        logger.error(f"Error saving profile for user {instance.username}: {e}")