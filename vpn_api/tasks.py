# vpn_api/tasks.py

from celery import shared_task
from django.utils import timezone
from .models import Subscription

@shared_task
def deactivate_subscription(subscription_id):
    try:
        subscription = Subscription.objects.get(id=subscription_id)
        if subscription.is_active and subscription.end_date <= timezone.now():
            subscription.is_active = False
            subscription.save()
            # Тут можно добавить логирование или уведомление пользователю
    except Subscription.DoesNotExist:
        pass  # Можно залогировать ошибку если нужно
