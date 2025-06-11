# vpn_api/views.py
import logging
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
from .services import extend_subscription, get_duration_delta, get_least_loaded_server, get_least_loaded_server_by_country
from uuid import uuid4, UUID


logger = logging.getLogger(__name__)


class BuySubscriptionView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        telegram_id = request.data.get("telegram_id")
        logger.debug(f"Получен telegram_id: {telegram_id}")

        if not telegram_id:
            return Response({"error": "telegram_id обязателен"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = VPNUser.objects.get(telegram_id=telegram_id)
            logger.debug(f"Пользователь найден: {user}")
        except VPNUser.DoesNotExist:
            logger.warning(f"Пользователь с telegram_id={telegram_id} не найден")
            return Response({"error": "Пользователь не найден"}, status=status.HTTP_404_NOT_FOUND)

        serializer = BuySubscriptionSerializer(data=request.data, context={'user': user})
        serializer.is_valid(raise_exception=True)

        plan = serializer.validated_data['plan']
        logger.debug(f"Выбранный план: ID={plan.id}, vpn_type={plan.vpn_type}, duration={plan.duration}")

        price = plan.get_current_price()
        logger.debug(f"Цена плана (со скидкой если есть): {price}")

        # Проверка на активную подписку того же типа
        active_subscriptions = user.subscriptions.filter(is_active=True, end_date__gt=timezone.now())
        same_type_sub = active_subscriptions.filter(plan__vpn_type=plan.vpn_type).first()

        if same_type_sub:
            logger.debug("Найдена активная подписка такого же типа, продлеваем...")

            if user.balance < price:
                logger.warning("Недостаточно средств для продления подписки")
                return Response({"error": "Недостаточно средств"}, status=402)

            try:
                extend_subscription(same_type_sub, plan)
                logger.debug("Подписка продлена успешно")
            except ValueError as e:
                logger.error(f"Ошибка продления: {str(e)}")
                return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            user.balance -= price
            user.save()
            logger.debug(f"Баланс после списания: {user.balance}")

            return Response({
                "message": "Подписка успешно продлена",
                "subscription_id": same_type_sub.id,
                "start_date": same_type_sub.start_date,
                "end_date": same_type_sub.end_date,
                "vless": same_type_sub.vless,
                "uuid": str(same_type_sub.uuid)
            }, status=status.HTTP_200_OK)

        # Новая подписка
        if user.balance < price:
            logger.warning("Недостаточно средств для новой подписки")
            return Response({"error": "Недостаточно средств"}, status=402)

        user_uuid = uuid4()
        logger.debug(f"Сгенерирован UUID: {user_uuid}")

        # Выбор сервера
        if plan.vpn_type == "country":
            country = request.data.get("country")
            if not country:
                return Response({"error": "Не указана страна"}, status=status.HTTP_400_BAD_REQUEST)
            server = get_least_loaded_server_by_country(country)
        else:
            server = get_least_loaded_server()

        if not server:
            logger.error("Нет доступных серверов")
            return Response({"error": "Нет доступных серверов"}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        logger.debug(f"Выбран сервер: {server.name} ({server.country})")

        # Генерация VLESS
        vless_result = create_vless(server, user_uuid)
        logger.debug(f"Результат создания VLESS: {vless_result}")

        if not vless_result["success"]:
            logger.error(f"Ошибка создания VLESS: {vless_result}")
            return Response({"error": "Ошибка создания VLESS"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        delta = get_duration_delta(plan.duration)
        if not delta:
            logger.error(f"Неизвестная длительность плана: {plan.duration}")
            return Response({"error": "Неизвестная длительность плана"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        start_date = timezone.now()
        end_date = start_date + delta
        logger.debug(f"Даты подписки: start={start_date}, end={end_date}")

        subscription = Subscription.objects.create(
            user=user,
            plan=plan,
            start_date=start_date,
            end_date=end_date,
            vless=vless_result["vless_link"],
            uuid=user_uuid
        )
        logger.info(f"Создана новая подписка: {subscription}")

        user.balance -= price
        user.save()
        logger.debug(f"Баланс после покупки: {user.balance}")

        return Response({
            "message": "Подписка успешно оформлена",
            "subscription_id": subscription.id,
            "start_date": subscription.start_date,
            "end_date": subscription.end_date,
            "vless": subscription.vless,
            "uuid": str(subscription.uuid)
        }, status=status.HTTP_201_CREATED)


class SubscriptionPlanListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        plans = SubscriptionPlan.objects.all()
        serializer = SubscriptionPlanSerializer(plans, many=True)
        return Response(serializer.data)
