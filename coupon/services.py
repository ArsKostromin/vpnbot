import uuid
from datetime import timedelta, datetime
from django.utils import timezone
from rest_framework import status
from vpn_api.models import SubscriptionPlan, Subscription
from .models import Coupon
from vpn_api.utils import create_vless
from vpn_api.services import extend_subscription, get_duration_delta, get_least_loaded_server, get_least_loaded_server_by_country
from uuid import uuid4


DURATION_DELTAS = {
    "5d": timedelta(days=5),
    "1m": timedelta(days=30),
    "3m": timedelta(days=90),
    "6m": timedelta(days=180),
    "1y": timedelta(days=365),
}

def get_duration_delta(duration):
    return DURATION_DELTAS.get(duration)

def apply_coupon_to_user(user, code, request=None):
    try:
        coupon = Coupon.objects.get(code__iexact=code)
    except Coupon.DoesNotExist:
        return {"data": {"detail": "Неверный промокод."}, "status": status.HTTP_404_NOT_FOUND}

    if coupon.is_used:
        return {"data": {"detail": "Промокод уже использован."}, "status": status.HTTP_400_BAD_REQUEST}

    if coupon.expiration_date and coupon.expiration_date < timezone.now():
        return {"data": {"detail": "Срок действия промокода истёк."}, "status": status.HTTP_400_BAD_REQUEST}

    # 🔹 Промокод на пополнение баланса
    if coupon.type == "balance":
        if not coupon.discount_amount:
            return {"data": {"detail": "У промокода не указана сумма пополнения."}, "status": status.HTTP_400_BAD_REQUEST}

        user.balance += coupon.discount_amount
        user.save(update_fields=["balance"])

        coupon.is_used = True
        coupon.used_by = user
        coupon.save(update_fields=["is_used", "used_by"])

        return {
            "data": {"detail": f"Баланс пополнен на {coupon.discount_amount}$."},
            "status": status.HTTP_200_OK,
        }

    # 🔹 Промокод на подписку
    elif coupon.type == "subscription":
        if not coupon.vpn_type or not coupon.duration:
            return {"data": {"detail": "Промокод некорректно настроен: vpn_type или duration не указаны."}, "status": status.HTTP_400_BAD_REQUEST}

        # Костыль: если 5d, то подсовываем 1m как duration в подписку
        actual_duration = '5d' if coupon.duration == '5d' else coupon.duration
        plan = SubscriptionPlan.objects.filter(
            vpn_type=coupon.vpn_type,
            duration=actual_duration
        ).first()

        delta = get_duration_delta(coupon.duration)
        if not delta:
            return {"data": {"detail": "Неизвестная длительность подписки."}, "status": status.HTTP_400_BAD_REQUEST}

        # Определяем сервер
        if coupon.vpn_type == "country":
            country = request.data.get("country") if request else None
            if not country:
                return {"data": {"detail": "Для этого типа промокода необходимо указать страну."}, "status": status.HTTP_400_BAD_REQUEST}
            server = get_least_loaded_server_by_country(country)
        else:
            server = get_least_loaded_server()

        if not server:
            return {"data": {"detail": "Нет доступных VPN-серверов."}, "status": status.HTTP_503_SERVICE_UNAVAILABLE}

        # Генерация UUID
        user_uuid = uuid4()

        # Создание VLESS-конфига
        vless_result = create_vless(server, user_uuid)

        if not vless_result.get("success"):
            return {
                "data": {"detail": "Ошибка при создании VLESS-конфига."},
                "status": status.HTTP_500_INTERNAL_SERVER_ERROR,
            }

        start_date = timezone.now()
        end_date = start_date + delta

        subscription = Subscription.objects.create(
            user=user,
            plan=plan,
            start_date=start_date,
            end_date=end_date,
            vless=vless_result["vless_link"],
            uuid=user_uuid,
            server=server
        )

        coupon.is_used = True
        coupon.used_by = user
        coupon.save(update_fields=["is_used", "used_by"])

        return {
            "data": {
                "detail": f"Промо-подписка активирована на {coupon.duration}.",
                "subscription_id": subscription.id,
                "start_date": subscription.start_date,
                "end_date": subscription.end_date,
                "vless": subscription.vless,
                "uuid": str(subscription.uuid)
            },
            "status": status.HTTP_200_OK,
        }

    return {"data": {"detail": "Неизвестный тип промокода."}, "status": status.HTTP_400_BAD_REQUEST}


def generate_coupon_for_user(user):
    code = f"VPN-{uuid.uuid4().hex[:6].upper()}"

    promo = Coupon.objects.create(
        code=code,
        type='subscription',
        expiration_date=datetime.now() + timedelta(days=5),
        vpn_type='serfing',  
        duration='5d',        
        is_used=False
    )

    return promo.code
