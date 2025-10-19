from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import UserProfile

@receiver(post_save, sender=User)
def manage_user_profile(sender, instance, created, **kwargs):
    """
    Create or update UserProfile when User is created or saved
    """
    if created:
        UserProfile.objects.create(
            user=instance,
            current_credit_score=300,
            phone_number="",  # Placeholder or collect via form
            national_id="",   # Placeholder or collect via form
            date_of_birth=timezone.now().date(),  # Placeholder
            district="Unknown",
            traditional_authority="Unknown",
            village="Unknown",
            employment_status="unemployed",
        )
    else:
        if hasattr(instance, 'userprofile'):
            instance.userprofile.save()