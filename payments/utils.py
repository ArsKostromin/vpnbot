from decimal import Decimal
from user.models import VPNUser
import logging

logger = logging.getLogger(__name__)

def apply_payment(user: VPNUser, amount: Decimal):
    try:
        logger.info(f"Пополнение {amount} для пользователя {user.telegram_id}")
        user.balance += amount
        user.save()

        if user.referred_by:
            bonus = amount * Decimal('0.10')
            user.referred_by.balance += bonus
            user.referred_by.save()
            user.got_referral_bonus = True
            user.save()
    except Exception as e:
        logger.exception(f"Ошибка при пополнении баланса: {e}")
