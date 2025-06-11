from django.utils import timezone
from vpn_api.models import Subscription
from celery import shared_task
from .utils import delete_vless


@shared_task
def check_expired_subscriptions():
    now = timezone.now()
    expired_subs = Subscription.objects.filter(is_active=True, end_date__lte=now)

    for sub in expired_subs:
        sub.is_active = False
        sub.save()

        if sub.uuid and sub.server:
            try:
                success = delete_vless(sub.server, str(sub.uuid))
                if success:
                    print(f"[check_expired_subscriptions] VLESS удалён: {sub.uuid}")
                else:
                    print(f"[check_expired_subscriptions] Не удалось удалить VLESS: {sub.uuid}")
            except Exception as e:
                print(f"[check_expired_subscriptions] Ошибка при удалении VLESS: {e}")
