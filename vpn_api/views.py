#vpn_api/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework import status
from .serializers import BuySubscriptionSerializer, SubscriptionPlanSerializer
from .models import Subscription, SubscriptionPlan
from user.models import VPNUser
from django.utils import timezone
from datetime import timedelta
from .utils import create_vless, delete_vless  # пусть функция будет там
from django.shortcuts import render

class BuySubscriptionView(APIView):
    permission_classes = [AllowAny]  # Разрешаем доступ всем (можно ограничить, если нужно)

    def post(self, request):
        # Получаем telegram_id из тела запроса
        telegram_id = request.data.get("telegram_id")
        if not telegram_id:
            return Response({"error": "telegram_id обязателен"}, status=status.HTTP_400_BAD_REQUEST)

        # Пытаемся найти пользователя по telegram_id
        try:
            user = VPNUser.objects.get(telegram_id=telegram_id)
        except VPNUser.DoesNotExist:
            return Response({"error": "Пользователь не найден"}, status=status.HTTP_404_NOT_FOUND)

        # Валидируем переданные данные сериализатором
        serializer = BuySubscriptionSerializer(data=request.data, context={'user': user})
        serializer.is_valid(raise_exception=True)

        plan = serializer.validated_data['plan']  # Получаем выбранный тарифный план

        # Проверяем, есть ли у пользователя активные подписки, срок которых ещё не истёк
        active_subscriptions = user.subscriptions.filter(is_active=True, end_date__gt=timezone.now())

        if active_subscriptions.exists():
            # Если уже есть подписка с таким же типом VPN, продолжаем её с момента окончания
            same_type_sub = active_subscriptions.filter(plan__vpn_type=plan.vpn_type).first()
            if same_type_sub:
                start_date = same_type_sub.end_date
            else:
                # Иначе деактивируем все старые и начинаем новую с текущего момента
                active_subscriptions.update(is_active=False)
                start_date = timezone.now()
        else:
            start_date = timezone.now()

        # Проверка на наличие достаточного баланса
        if user.balance < plan.price:
            return Response({"error": "Недостаточно средств"}, status=status.HTTP_400_BAD_REQUEST)

        # Списываем средства с баланса
        user.balance -= plan.price
        user.save()


        vless_result = create_vless(user.uuid)
        if not vless_result["success"]:
            return Response({"error": "Ошибка создания VLESS"}, status=500)

        # Создаём новую подписку
        subscription = Subscription.objects.create(
            user=user,
            plan=plan,
            start_date=start_date,
            vless=vless_result["vless_link"],
        )

        # Возвращаем инфу об успешно оформленной подписке
        return Response({
            "message": f"Подписка успешно оформлена",
            "subscription_id": subscription.id,
            "start_date": subscription.start_date,
            "end_date": subscription.end_date,
            "vless": subscription.vless  # На этом этапе может быть пусто, если выше не вызывался FastAPI
        }, status=status.HTTP_201_CREATED)




class SubscriptionPlanListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        plans = SubscriptionPlan.objects.all()
        serializer = SubscriptionPlanSerializer(plans, many=True)
        return Response(serializer.data)
