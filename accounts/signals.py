from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from .models import UserProfile, EmailVerification

User = get_user_model()

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Create a UserProfile instance when a new User is created."""
    if created:
        UserProfile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """Save the UserProfile instance when the User is saved."""
    if hasattr(instance, 'profile'):
        instance.profile.save()

@receiver(post_save, sender=User)
def create_email_verification(sender, instance, created, **kwargs):
    """Create an EmailVerification instance when a new User is created."""
    if created and not instance.is_email_verified:
        # Delete any existing unverified email verifications for this user
        EmailVerification.objects.filter(user=instance, is_verified=False).delete()
        
        # Create new email verification
        expires_at = timezone.now() + timedelta(hours=24)
        EmailVerification.objects.create(
            user=instance,
            expires_at=expires_at
        )

@receiver(pre_save, sender=User)
def normalize_user_email(sender, instance, **kwargs):
    """Normalize email address before saving."""
    if instance.email:
        instance.email = instance.email.lower().strip()
