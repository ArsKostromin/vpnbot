# vpn_api/views.py
import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework import status
from .serializers import BuySubscriptionSerializer, SubscriptionPlanSerializer, СountriesSerializer
from .models import Subscription, SubscriptionPlan, VPNServer
from user.models import VPNUser
from django.utils import timezone
import uuid
from .utils import create_vless
from .services import extend_subscription, get_duration_delta, get_least_loaded_server, get_least_loaded_server_by_country
from uuid import uuid4, UUID
from decimal import Decimal


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

        # Проверка на бан пользователя
        if user.is_banned:
            logger.warning(f"Забаненный пользователь {telegram_id} пытается купить подписку")
            return Response({
                "error": "Ваш аккаунт заблокирован",
                "ban_reason": user.ban_reason or "Причина не указана"
            }, status=status.HTTP_403_FORBIDDEN)

        serializer = BuySubscriptionSerializer(data=request.data, context={'user': user})
        serializer.is_valid(raise_exception=True)

        plan = serializer.validated_data['plan']
        logger.debug(f"Выбранный план: ID={plan.id}, vpn_type={plan.vpn_type}, duration={plan.duration}")

        price = serializer.validated_data['price']
        logger.debug(f"Цена плана (со скидкой если есть): {price}")

        # Проверка на активную подписку того же типа (только если не country)
        if plan.vpn_type != "country":
            active_subscriptions = user.subscriptions.filter(is_active=True, end_date__gt=timezone.now())
            same_type_sub = active_subscriptions.filter(plan__vpn_type=plan.vpn_type).first()
            if same_type_sub:
                logger.debug("У пользователя уже есть активная подписка такого типа")
                return Response({
                    "error": "У вас уже есть активная подписка этого типа",
                    "subscription_id": same_type_sub.id,
                    "start_date": same_type_sub.start_date,
                    "end_date": same_type_sub.end_date,
                    "vless": same_type_sub.vless,
                    "uuid": str(same_type_sub.uuid)
                }, status=status.HTTP_409_CONFLICT)

        # --- Одноразовая скидка для пригласившего ---
        if serializer.validated_data.get('referral_discount_applied'):
            user.referral_discount_used = True
            user.save()
            logger.info(f"Пользователь {user.telegram_id} использовал одноразовую скидку 10% на покупку подписки.")
        # --- Конец логики скидки ---

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
            uuid=user_uuid,
            server=server
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
        user = None
        telegram_id = request.query_params.get('telegram_id')
        logger.info(f"SubscriptionPlanListView: telegram_id={telegram_id}")
        
        if telegram_id:
            try:
                from user.models import VPNUser
                user = VPNUser.objects.get(telegram_id=telegram_id)
                logger.info(f"Пользователь найден: {user}, referrals_count={user.referrals.count()}")
            except VPNUser.DoesNotExist:
                user = None
                logger.warning(f"Пользователь с telegram_id={telegram_id} не найден")
        else:
            logger.info("telegram_id не передан в query параметрах")
        
        serializer = SubscriptionPlanSerializer(plans, many=True, context={'user': user})
        logger.info(f"Сериализатор создан с user={user}")
        return Response(serializer.data)


class CountriesPlanListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        countries = VPNServer.objects.filter(is_active=True)
        serializer = СountriesSerializer(countries, many=True)
        return Response(serializer.data)