# vpn_api/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework import status
from .serializers import BuySubscriptionSerializer, SubscriptionPlanSerializer
from .models import Subscription, SubscriptionPlan
from user.models import VPNUser
from django.utils import timezone
import uuid
from .utils import create_vless
from .services import extend_subscription, get_duration_delta
import logging

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

class BuySubscriptionView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        telegram_id = request.data.get("telegram_id")
        print(f"[DEBUG] Получен telegram_id: {telegram_id}")
        if not telegram_id:
            return Response({"error": "telegram_id обязателен"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = VPNUser.objects.get(telegram_id=telegram_id)
            print(f"[DEBUG] Пользователь найден: {user}")
        except VPNUser.DoesNotExist:
            print(f"[ERROR] Пользователь с telegram_id={telegram_id} не найден")
            return Response({"error": "Пользователь не найден"}, status=status.HTTP_404_NOT_FOUND)

        serializer = BuySubscriptionSerializer(data=request.data, context={'user': user})
        serializer.is_valid(raise_exception=True)

        plan = serializer.validated_data['plan']
        print(f"[DEBUG] Выбранный план: ID={plan.id}, vpn_type={plan.vpn_type}, duration={plan.duration}")

        price = plan.get_current_price()
        print(f"[DEBUG] Цена плана (со скидкой если есть): {price}")

        active_subscriptions = user.subscriptions.filter(is_active=True, end_date__gt=timezone.now())
        same_type_sub = active_subscriptions.filter(plan__vpn_type=plan.vpn_type).first()

        if same_type_sub:
            print(f"[DEBUG] Найдена активная подписка такого же типа, продлеваем...")
            try:
                extend_subscription(same_type_sub, plan)
                print(f"[DEBUG] Подписка продлена успешно")
            except ValueError as e:
                print(f"[ERROR] Ошибка продления: {str(e)}")
                return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            user.balance -= price
            user.save()
            print(f"[DEBUG] Баланс после списания: {user.balance}")

            return Response({
                "message": "Подписка успешно продлена",
                "subscription_id": same_type_sub.id,
                "start_date": same_type_sub.start_date,
                "end_date": same_type_sub.end_date,
                "vless": same_type_sub.vless,
                "uuid": same_type_sub.uuid
            }, status=status.HTTP_200_OK)

        # Новая подписка
        user_uuid = uuid.uuid4()
        print(f"[DEBUG] Сгенерирован UUID: {user_uuid}")
        vless_result = create_vless(user_uuid)
        print(f"[DEBUG] Результат создания VLESS: {vless_result}")

        if not vless_result["success"]:
            print(f"[ERROR] Ошибка создания VLESS: {vless_result}")
            return Response({"error": "Ошибка создания VLESS"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        delta = get_duration_delta(plan.duration)
        print(f"[DEBUG] Расчитанная длительность (delta): {delta}")

        if not delta:
            print(f"[ERROR] Неизвестная длительность плана: {plan.duration}")
            return Response({"error": "Неизвестная длительность плана"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        start_date = timezone.now()
        end_date = start_date + delta
        print(f"[DEBUG] Даты подписки: start={start_date}, end={end_date}")

        subscription = Subscription.objects.create(
            user=user,
            plan=plan,
            start_date=start_date,
            end_date=end_date,
            vless=vless_result["vless_link"],
            uuid=user_uuid
        )
        print(f"[DEBUG] Создана подписка: {subscription}")

        user.balance -= price
        user.save()
        print(f"[DEBUG] Баланс после покупки: {user.balance}")

        return Response({
            "message": "Подписка успешно оформлена",
            "subscription_id": subscription.id,
            "start_date": subscription.start_date,
            "end_date": subscription.end_date,
            "vless": subscription.vless,
            "uuid": subscription.uuid
        }, status=status.HTTP_201_CREATED)



class SubscriptionPlanListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        plans = SubscriptionPlan.objects.all()
        serializer = SubscriptionPlanSerializer(plans, many=True)
        return Response(serializer.data)
