from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from django.utils import timezone
from vpn_api.models import SubscriptionPlan, Subscription
from .models import Coupon
from user.models import VPNUser
from rest_framework.permissions import AllowAny
import uuid
from datetime import timedelta, datetime
from rest_framework.decorators import api_view

class ApplyCouponView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        code = request.data.get("code", "").strip()
        
        telegram_id = request.data.get("telegram_id")
        
        if not telegram_id:
            return Response({"error": "telegram_id обязателен"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = VPNUser.objects.get(telegram_id=telegram_id)
        except VPNUser.DoesNotExist:
            return Response({"error": "Пользователь не найден"}, status=status.HTTP_404_NOT_FOUND)

        if not code:
            return Response({"detail": "Промокод не указан."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            coupon = Coupon.objects.get(code=code)
        except Coupon.DoesNotExist:
            return Response({"detail": "Неверный промокод."}, status=status.HTTP_404_NOT_FOUND)

        if coupon.is_used:
            return Response({"detail": "Промокод уже был использован."}, status=status.HTTP_400_BAD_REQUEST)

        if coupon.expiration_date < timezone.now():
            return Response({"detail": "Срок действия промокода истёк."}, status=status.HTTP_400_BAD_REQUEST)

        if coupon.type == "balance":
            user.balance += coupon.discount_amount
            user.save()
            coupon.is_used = True
            coupon.used_by = user
            coupon.save()
            return Response({"detail": f"Баланс пополнен на {coupon.discount_amount}₽."})

        elif coupon.type == "subscription":
            plan = SubscriptionPlan.objects.filter(vpn_type=coupon.vpn_type, duration=coupon.duration).first()
            if not plan:
                return Response({"detail": "Не удалось найти соответствующий тариф."}, status=status.HTTP_400_BAD_REQUEST)

            # Создаём подписку
            Subscription.objects.create(user=user, plan=plan)
            coupon.is_used = True
            coupon.used_by = user
            coupon.save()
            return Response({"detail": f"Подписка {plan} активирована."})

        return Response({"detail": "Неверный тип промокода."}, status=status.HTTP_400_BAD_REQUEST)



@api_view(['POST'])
def generate_promo_code(request):
    telegram_id = request.data.get("telegram_id")

    if not telegram_id:
        return Response({"error": "telegram_id is required"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        user = VPNUser.objects.get(telegram_id=telegram_id)
    except VPNUser.DoesNotExist:
        return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)

    # Генерация уникального кода
    code = f"VPN-{uuid.uuid4().hex[:6].upper()}"

    # Создание купона на 3 дня
    promo = Coupon.objects.create(
        code=code,
        type='subscription',
        expiration_date=datetime.now() + timedelta(days=5),
        vpn_type='solo',
        duration='1m',
        is_used=False
    )

    return Response({"promo_code": promo.code})