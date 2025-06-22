# views.py
import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .models import VPNUser
from vpn_api.models import Subscription
from .serializers import SubscriptionSerializer, UserInfoSerializer, RegisterUserSerializer
from .services import get_user_by_telegram_id, register_user_with_referral


logger = logging.getLogger(__name__)


class RegisterUserView(APIView):
    """
    Эндпоинт для регистрации пользователя по telegram_id и необязательному referral_code.
    """

    def post(self, request):
        serializer = RegisterUserSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        telegram_id = serializer.validated_data["telegram_id"]
        referral_code = serializer.validated_data.get("referral_code")

        logger.info(f"Получен запрос на регистрацию: telegram_id={telegram_id}, referral_code={referral_code}")
        print("Реферал код:", referral_code)
        user, created, error_response = register_user_with_referral(telegram_id, referral_code)
        if error_response:
            logger.warning(f"Ошибка при регистрации пользователя {telegram_id}: {error_response.data}")
            return error_response

        # Проверка на бан пользователя (если пользователь уже существовал)
        if not created and user.is_banned:
            logger.warning(f"Забаненный пользователь {telegram_id} пытается зарегистрироваться")
            return Response({
                "error": "Ваш аккаунт заблокирован",
                "ban_reason": user.ban_reason or "Причина не указана"
            }, status=status.HTTP_403_FORBIDDEN)

        logger.info(f"Пользователь {telegram_id} зарегистрирован. New: {created}, link_code: {user.link_code}")

        return Response({
            "created": created,
            "link_code": user.link_code,
        }, status=status.HTTP_201_CREATED)


class UserSubscriptionsAPIView(APIView):
    """
    Эндпоинт для получения всех подписок пользователя по telegram_id.
    """
    def get(self, request, telegram_id):
        user = get_user_by_telegram_id(telegram_id)
        if isinstance(user, Response):
            return user

        subscriptions = Subscription.objects.filter(user=user)
        serializer = SubscriptionSerializer(subscriptions, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class UserBalanceAndLinkAPIView(APIView):
    """
    Эндпоинт для получения баланса и кода привязки пользователя по telegram_id.
    """
    def get(self, request, telegram_id):
        user = get_user_by_telegram_id(telegram_id)
        if isinstance(user, Response):
            return user

        serializer = UserInfoSerializer(user)
        return Response(serializer.data, status=status.HTTP_200_OK)