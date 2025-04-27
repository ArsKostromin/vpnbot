#signals
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Subscription
from .tasks import deactivate_subscription

@receiver(post_save, sender=Subscription)
def schedule_deactivation_on_create(sender, instance, created, **kwargs):
    if created and instance.end_date:
        deactivate_subscription.apply_async(
            args=[instance.id],
            eta=instance.end_date
        )
