from decimal import Decimal
from user.models import VPNUser
import logging

logger = logging.getLogger(__name__)

def apply_payment(user: VPNUser, amount: Decimal):
    try:
        logger.info(f"Пополнение {amount} для пользователя {user.telegram_id}")
        user.balance += amount
        user.save()

        # Логика одноразовой скидки для пригласившего
        if user.referred_by:
            inviter = user.referred_by
            # Если у пригласившего есть хотя бы один приглашённый и скидка не использована
            if not inviter.referral_discount_used and inviter.referrals.exists():
                discount = amount * Decimal('0.10')
                inviter.balance += discount
                inviter.referral_discount_used = True
                inviter.save()
                logger.info(f"Пригласившему пользователю {inviter.telegram_id} начислена одноразовая скидка 10% ({discount})")
    except Exception as e:
        logger.exception(f"Ошибка при пополнении баланса: {e}")
