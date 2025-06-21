# services.py
from rest_framework.response import Response
from rest_framework import status
from .models import VPNUser
import logging

logger = logging.getLogger(__name__)


def get_user_by_telegram_id(telegram_id):
    """
    Получение пользователя по telegram_id или возврат ошибки.
    """
    if not telegram_id:
        return Response({"error": "telegram_id is required"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        return VPNUser.objects.get(telegram_id=telegram_id)
    except VPNUser.DoesNotExist:
        return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)


def register_user_with_referral(telegram_id, referral_code=None):
    """
    Регистрация пользователя и обработка реферального кода.
    """
    user, created = VPNUser.objects.get_or_create(telegram_id=telegram_id)

    if not created:  # and user.is_banned
        return user, created, Response({"error": "Пользователь заблокирован"}, status=status.HTTP_403_FORBIDDEN)

    if referral_code and not user.referred_by:
        try:
            referrer = VPNUser.objects.get(link_code=referral_code)
            if referrer.id != user.id:
                user.referred_by = referrer
                user.save()
        except VPNUser.DoesNotExist:
            logger.warning(f"Invalid referral code: {referral_code}")

    return user, created, None
