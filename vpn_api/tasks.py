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

        if sub.user and sub.user.uuid:
            try:
                result = delete_vless(str(sub.user.uuid))
                if result.get("success"):
                    print(f"[check_expired_subscriptions] VLESS удалён: {sub.user.uuid}")
                else:
                    print(f"[check_expired_subscriptions] Ошибка удаления VLESS: {result.get('message')}")
            except Exception as e:
                print(f"[check_expired_subscriptions] Ошибка при вызове delete_vless: {e}")