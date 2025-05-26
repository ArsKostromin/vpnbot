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


class BuySubscriptionView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        telegram_id = request.data.get("telegram_id")
        if not telegram_id:
            return Response({"error": "telegram_id обязателен"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = VPNUser.objects.get(telegram_id=telegram_id)
        except VPNUser.DoesNotExist:
            return Response({"error": "Пользователь не найден"}, status=status.HTTP_404_NOT_FOUND)

        serializer = BuySubscriptionSerializer(data=request.data, context={'user': user})
        serializer.is_valid(raise_exception=True)

        plan = serializer.validated_data['plan']
        price = plan.get_current_price()  # 💰 используем цену со скидкой, если она активна

        # Активные подписки такого же типа
        active_subscriptions = user.subscriptions.filter(is_active=True, end_date__gt=timezone.now())
        same_type_sub = active_subscriptions.filter(plan__vpn_type=plan.vpn_type).first()

        if same_type_sub:
            # Продление подписки
            try:
                extend_subscription(same_type_sub, plan)
            except ValueError as e:
                return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            user.balance -= price
            user.save()

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
        vless_result = create_vless(user_uuid)
        if not vless_result["success"]:
            return Response({"error": "Ошибка создания VLESS"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        delta = get_duration_delta(plan.duration)
        if not delta:
            return Response({"error": "Неизвестная длительность плана"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        start_date = timezone.now()
        end_date = start_date + delta

        subscription = Subscription.objects.create(
            user=user,
            plan=plan,
            start_date=start_date,
            end_date=end_date,
            vless=vless_result["vless_link"],
            uuid=user_uuid
        )

        user.balance -= price
        user.save()

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
