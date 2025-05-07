import uuid
from datetime import timedelta, datetime
from django.utils import timezone
from rest_framework import status
from vpn_api.models import SubscriptionPlan, Subscription
from .models import Coupon


def apply_coupon_to_user(user, code):
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

        # Создаём подписку
        Subscription.objects.create(user=user, plan=plan)

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
