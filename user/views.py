# views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import VPNUser
from vpn_api.models import Subscription
from .serializers import SubscriptionSerializer, UserInfoSerializer


# Эндпоинт для регистрации пользователя по telegram_id
class RegisterUserView(APIView):
    def post(self, request):
        telegram_id = request.data.get("telegram_id")
        referral_code = request.data.get("referral_code")  # новый параметр

        if not telegram_id:
            return Response({"error": "telegram_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        user, created = VPNUser.objects.get_or_create(telegram_id=telegram_id)

        # если заблокирован — отказ
        if not created and user.is_banned:
            return Response({"error": "Пользователь заблокирован"}, status=status.HTTP_403_FORBIDDEN)

        # только при первом создании и если указали рефералку
        if created and referral_code:
            try:
                referrer = VPNUser.objects.get(link_code=referral_code)
                if referrer.id != user.id:
                    user.referred_by = referrer
                    user.save()
            except VPNUser.DoesNotExist:
                pass  # просто игнорируем неверный код

        return Response({
            "created": created,
            "link_code": user.link_code,
        }, status=status.HTTP_201_CREATED)


# Эндпоинт для получения всех подписок пользователя
class UserSubscriptionsAPIView(APIView):
    def get(self, request, telegram_id):
        # Проверка: передан ли telegram_id
        if not telegram_id:
            return Response({"error": "telegram_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Поиск пользователя по telegram_id
            user = VPNUser.objects.get(telegram_id=telegram_id)
        except VPNUser.DoesNotExist:
            return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)

        # Получение всех подписок пользователя
        subscriptions = Subscription.objects.filter(user=user)

        # Сериализация списка подписок
        serializer = SubscriptionSerializer(subscriptions, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


# Эндпоинт для получения баланса и кода привязки пользователя
class UserBalanceAndLinkAPIView(APIView):
    def get(self, request, telegram_id):
        # Проверка: передан ли telegram_id
        if not telegram_id:
            return Response({"error": "telegram_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Поиск пользователя по telegram_id
            user = VPNUser.objects.get(telegram_id=telegram_id)
        except VPNUser.DoesNotExist:
            return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)

        # Сериализация информации о пользователе (баланс + код привязки)
        serializer = UserInfoSerializer(user)
        return Response(serializer.data, status=status.HTTP_200_OK)