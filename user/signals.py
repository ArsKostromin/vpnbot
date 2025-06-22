from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django.utils import timezone
from .models import VPNUser
from vpn_api.models import Subscription
from vpn_api.utils import delete_vless, create_vless
import logging

logger = logging.getLogger(__name__)

# Глобальная переменная для хранения старого состояния
_old_ban_status = {}


@receiver(pre_save, sender=VPNUser)
def store_old_ban_status(sender, instance, **kwargs):
    """
    Сохраняет старое состояние бана перед сохранением.
    """
    if instance.pk:  # Только для существующих пользователей
        try:
            old_instance = VPNUser.objects.get(pk=instance.pk)
            _old_ban_status[instance.pk] = old_instance.is_banned
        except VPNUser.DoesNotExist:
            _old_ban_status[instance.pk] = False


@receiver(post_save, sender=VPNUser)
def handle_user_ban_status_change(sender, instance, created, **kwargs):
    """
    Обрабатывает изменения статуса бана пользователя.
    При бане - деактивирует подписки и удаляет VLESS.
    При разбане - восстанавливает активные подписки и создает VLESS.
    """
    if created:
        return  # Новый пользователь, ничего не делаем
    
    try:
        # Получаем старое состояние из глобальной переменной
        old_is_banned = _old_ban_status.get(instance.pk, False)
        
        # Проверяем, изменился ли статус бана
        if old_is_banned != instance.is_banned:
            logger.info(f"Статус бана изменился для пользователя {instance.pk}: {old_is_banned} -> {instance.is_banned}")
            
            if instance.is_banned:
                # Пользователь забанен
                handle_user_banned(instance)
            else:
                # Пользователь разбанен
                handle_user_unbanned(instance)
        
        # Очищаем старое состояние
        if instance.pk in _old_ban_status:
            del _old_ban_status[instance.pk]
                
    except Exception as e:
        logger.error(f"Ошибка при обработке изменения статуса бана для пользователя {instance.pk}: {e}")


def handle_user_banned(user):
    """
    Обрабатывает бан пользователя:
    - Деактивирует все активные подписки
    - Удаляет VLESS ключи с серверов
    - Отправляет уведомление пользователю
    """
    logger.info(f"Обработка бана пользователя {user.pk} (Telegram ID: {user.telegram_id})")
    
    # Получаем все активные подписки пользователя
    active_subscriptions = user.subscriptions.filter(is_active=True)
    
    for subscription in active_subscriptions:
        try:
            # Деактивируем подписку
            subscription.is_active = False
            subscription.save(update_fields=['is_active'])
            
            # Удаляем VLESS с сервера
            if subscription.server and subscription.uuid:
                success = delete_vless(subscription.server, str(subscription.uuid))
                if success:
                    logger.info(f"VLESS удален для подписки {subscription.pk} (UUID: {subscription.uuid})")
                else:
                    logger.error(f"Не удалось удалить VLESS для подписки {subscription.pk} (UUID: {subscription.uuid})")
                    
        except Exception as e:
            logger.error(f"Ошибка при обработке подписки {subscription.pk}: {e}")
    
    # Отправляем уведомление пользователю
    send_ban_notification(user)


def handle_user_unbanned(user):
    """
    Обрабатывает разбан пользователя:
    - Восстанавливает подписки, срок действия которых не истек
    - Создает VLESS ключи на серверах
    - Отправляет уведомление пользователю
    """
    logger.info(f"Обработка разбана пользователя {user.pk} (Telegram ID: {user.telegram_id})")
    
    # Получаем все неактивные подписки пользователя, срок действия которых не истек
    from django.utils import timezone
    now = timezone.now()
    
    inactive_subscriptions = user.subscriptions.filter(
        is_active=False,
        end_date__gt=now
    )
    
    restored_count = 0
    
    for subscription in inactive_subscriptions:
        try:
            # Активируем подписку
            subscription.is_active = True
            subscription.save(update_fields=['is_active'])
            
            # Создаем VLESS на сервере
            if subscription.server and subscription.uuid:
                vless_result = create_vless(subscription.server, str(subscription.uuid))
                if vless_result.get("success"):
                    # Обновляем VLESS ссылку
                    subscription.vless = vless_result.get("vless_link")
                    subscription.save(update_fields=['vless'])
                    logger.info(f"VLESS восстановлен для подписки {subscription.pk} (UUID: {subscription.uuid})")
                    restored_count += 1
                else:
                    logger.error(f"Не удалось создать VLESS для подписки {subscription.pk} (UUID: {subscription.uuid})")
                    
        except Exception as e:
            logger.error(f"Ошибка при восстановлении подписки {subscription.pk}: {e}")
    
    # Отправляем уведомление пользователю
    send_unban_notification(user, restored_count)


def send_ban_notification(user):
    """
    Отправляет уведомление о бане пользователю через Telegram бота.
    """
    if not user.telegram_id:
        logger.warning(f"Не удалось отправить уведомление о бане: у пользователя {user.pk} нет telegram_id")
        return
    
    try:
        import requests
        
        message = (
            f"🚫 Ваш аккаунт заблокирован.\n\n"
            f"Причина: {user.ban_reason or 'Не указана'}\n\n"
            f"Для уточнения деталей обратитесь в службу поддержки."
        )
        
        # Отправляем уведомление через API бота
        response = requests.post(
            "http://vpn_bot:8081/notify",
            json={
                "tg_id": user.telegram_id,
                "message": message,
                "type": "ban_notification"
            },
            timeout=5
        )
        
        if response.status_code == 200:
            logger.info(f"Уведомление о бане отправлено пользователю {user.telegram_id}")
        else:
            logger.error(f"Ошибка при отправке уведомления о бане: {response.status_code} {response.text}")
            
    except Exception as e:
        logger.error(f"Ошибка при отправке уведомления о бане пользователю {user.telegram_id}: {e}")


def send_unban_notification(user, restored_count):
    """
    Отправляет уведомление о разбане пользователю через Telegram бота.
    """
    if not user.telegram_id:
        logger.warning(f"Не удалось отправить уведомление о разбане: у пользователя {user.pk} нет telegram_id")
        return
    
    try:
        import requests
        
        message = (
            f"✅ Ваш аккаунт разблокирован!\n\n"
            f"Все ваши активные подписки, срок действия которых еще не истек, были восстановлены."
        )
        
        if restored_count > 0:
            message += f"\n\nВосстановлено подписок: {restored_count}"
        
        # Отправляем уведомление через API бота
        response = requests.post(
            "http://vpn_bot:8081/notify",
            json={
                "tg_id": user.telegram_id,
                "message": message,
                "type": "unban_notification"
            },
            timeout=5
        )
        
        if response.status_code == 200:
            logger.info(f"Уведомление о разбане отправлено пользователю {user.telegram_id}")
        else:
            logger.error(f"Ошибка при отправке уведомления о разбане: {response.status_code} {response.text}")
            
    except Exception as e:
        logger.error(f"Ошибка при отправке уведомления о разбане пользователю {user.telegram_id}: {e}") 