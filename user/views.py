# views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .models import VPNUser
from vpn_api.models import Subscription
from .serializers import SubscriptionSerializer, UserInfoSerializer, RegisterUserSerializer
from .services import get_user_by_telegram_id, register_user_with_referral


class RegisterUserView(APIView):
    """
    Эндпоинт для регистрации пользователя по telegram_id и необязательному referral_code.
    """
    def post(self, request):
        serializer = RegisterUserSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        telegram_id = serializer.validated_data["telegram_id"]
        referral_code = serializer.validated_data.get("referral_code")

        user, created, error_response = register_user_with_referral(telegram_id, referral_code)
        if error_response:
            return error_response

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