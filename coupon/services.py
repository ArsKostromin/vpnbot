import uuid
from datetime import timedelta, datetime
from django.utils import timezone
from rest_framework import status
from vpn_api.models import SubscriptionPlan, Subscription
from .models import Coupon
from vpn_api.utils import create_vless
from vpn_api.services import extend_subscription, get_duration_delta, get_least_loaded_server, get_least_loaded_server_by_country


def apply_coupon_to_user(user, code, request=None):
    try:
        coupon = Coupon.objects.get(code__iexact=code)
    except Coupon.DoesNotExist:
        return {"data": {"detail": "Неверный промокод."}, "status": status.HTTP_404_NOT_FOUND}

    if coupon.is_used:
        return {"data": {"detail": "Промокод уже был использован."}, "status": status.HTTP_400_BAD_REQUEST}

    if coupon.expiration_date < timezone.now():
        return {"data": {"detail": "Срок действия промокода истёк."}, "status": status.HTTP_400_BAD_REQUEST}

    if coupon.type == "balance":
        user.balance += coupon.discount_amount
        user.save()

        coupon.is_used = True
        coupon.used_by = user
        coupon.save()

        return {"data": {"detail": f"Баланс пополнен на {coupon.discount_amount}₽."}, "status": status.HTTP_200_OK}

    elif coupon.type == "subscription":
        plan = SubscriptionPlan.objects.filter(
            vpn_type=coupon.vpn_type, duration=coupon.duration
        ).first()

        if not plan:
            return {
                "data": {"detail": "Не удалось найти соответствующий тариф."},
                "status": status.HTTP_400_BAD_REQUEST,
            }

        # Выбираем сервер в зависимости от типа
        if plan.vpn_type == "country":
            country = None
            if request:
                country = request.data.get("country")
            if not country:
                return {
                    "data": {"detail": "Для этого промокода необходимо указать страну."},
                    "status": status.HTTP_400_BAD_REQUEST,
                }
            server = get_least_loaded_server_by_country(country)
        else:
            server = get_least_loaded_server()

        if not server:
            return {
                "data": {"detail": "Нет доступных VPN-серверов."},
                "status": status.HTTP_503_SERVICE_UNAVAILABLE,
            }

        # Создаём подписку
        subscription = Subscription.objects.create(user=user, plan=plan, server=server)

        try:
            vless_result = create_vless(server, str(subscription.uuid))
        except Exception as e:
            subscription.delete()
            return {
                "data": {"detail": f"Ошибка при создании VLESS: {str(e)}"},
                "status": status.HTTP_500_INTERNAL_SERVER_ERROR,
            }

        if not vless_result.get("success"):
            subscription.delete()
            return {
                "data": {"detail": "VLESS не был создан. Попробуйте позже."},
                "status": status.HTTP_500_INTERNAL_SERVER_ERROR,
            }

        subscription.vless = vless_result["vless_link"]
        subscription.save()

        coupon.is_used = True
        coupon.used_by = user
        coupon.save()

        return {
            "data": {"detail": f"Подписка {plan} активирована."},
            "status": status.HTTP_200_OK,
        }

    return {"data": {"detail": "Неверный тип промокода."}, "status": status.HTTP_400_BAD_REQUEST}


def generate_coupon_for_user(user):
    code = f"VPN-{uuid.uuid4().hex[:6].upper()}"

    promo = Coupon.objects.create(
        code=code,
        type='subscription',
        expiration_date=datetime.now() + timedelta(days=5),
        vpn_type='solo',
        duration='1m',
        is_used=False
    )

    return promo.code
