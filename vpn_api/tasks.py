from django.utils import timezone
from vpn_api.models import Subscription
from celery import shared_task

@shared_task
def check_expired_subscriptions():
    now = timezone.now()
    expired_subs = Subscription.objects.filter(is_active=True, end_date__lte=now)
    
    for sub in expired_subs:
        sub.is_active = False
        sub.save()
