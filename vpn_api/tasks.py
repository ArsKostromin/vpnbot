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

        # --- АВТОПРОДЛЕНИЕ ---
        if sub.auto_renew:
            user = sub.user
            plan = sub.plan
            price = plan.get_current_price()
            import logging
            logger = logging.getLogger(__name__)
            from payments.services import robokassa_recurring_charge
            
            if user.balance >= price:
                from uuid import uuid4
                from .utils import create_vless, get_duration_delta
                from .services import get_least_loaded_server

                # Выбираем сервер (аналогично обычной покупке)
                if plan.vpn_type == "country":
                    server = sub.server or get_least_loaded_server()
                else:
                    server = get_least_loaded_server()

                if not server:
                    logger.warning("[auto_renew] Нет доступных серверов для автопродления!")
                    continue

                user_uuid = uuid4()
                vless_result = create_vless(server, user_uuid)
                if not vless_result["success"]:
                    logger.warning(f"[auto_renew] Ошибка создания VLESS: {vless_result}")
                    continue

                delta = get_duration_delta(plan.duration)
                if not delta:
                    logger.warning(f"[auto_renew] Неизвестная длительность плана: {plan.duration}")
                    continue

                start_date = now
                end_date = start_date + delta

                Subscription.objects.create(
                    user=user,
                    plan=plan,
                    start_date=start_date,
                    end_date=end_date,
                    vless=vless_result["vless_link"],
                    uuid=user_uuid,
                    server=server,
                    auto_renew=True
                )
                user.balance -= price
                user.save()
                logger.warning(f"[auto_renew] Подписка успешно продлена для пользователя {user.telegram_id} с баланса")
            else:
                # --- Попытка автосписания с карты через Robokassa ---
                logger.warning(f"[auto_renew] Недостаточно средств для автопродления с баланса у пользователя {user.telegram_id}, пытаемся списать с карты через Robokassa...")
                success = robokassa_recurring_charge(user, price)
                if success:
                    logger.warning(f"[auto_renew] Запрос на автосписание отправлен для пользователя {user.telegram_id}. Ждём подтверждения от Robokassa.")
                    # Больше ничего не делаем! Ждём колбэка от Robokassa для пополнения баланса и продления подписки
                else:
                    sub.auto_renew = False
                    sub.save()
                    logger.warning(f"[auto_renew] Не удалось автосписание через Robokassa, auto_renew выключен для подписки {sub.id}")
