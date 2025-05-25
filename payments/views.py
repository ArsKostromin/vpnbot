# payments/views.py
import hashlib
from decimal import Decimal, InvalidOperation
import hmac
import requests
import json
from django.http import JsonResponse, HttpResponseForbidden
from django.views.decorators.csrf import csrf_exempt
from decimal import Decimal
from django.conf import settings
from django.http import HttpResponse
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.views import APIView

from user.models import VPNUser
from payments.models import Payment
from payments.cryptobot import generate_crypto_payment_link
from payments.utils import apply_payment
from payments.services import (
    generate_unique_inv_id,
    generate_robokassa_payment_link,
    verify_robokassa_signature
)
import logging

logger = logging.getLogger(__name__)


@api_view(["POST"])
def create_payment(request):
    """
    Создание Robokassa-платежа для пользователя.
    """
    telegram_id = request.data.get("telegram_id")
    amount = request.data.get("amount")

    if not telegram_id:
        return Response({"error": "telegram_id is required"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        amount = int(amount)
    except (ValueError, TypeError):
        return Response({"error": "Некорректная сумма."}, status=status.HTTP_400_BAD_REQUEST)

    user = VPNUser.objects.get(telegram_id=telegram_id)

    payment = Payment.objects.create(
        user=user,
        inv_id=generate_unique_inv_id(),
        amount=Decimal(amount),
        status=Payment.Status.PENDING,
        currency='Рубли'
    )

    payment_link = generate_robokassa_payment_link(payment)
    return Response({"payment_url": payment_link})


@api_view(["GET", "POST"])
def payment_result(request):
    """
    Обработка callback'а от Robokassa после оплаты.
    """
    out_sum = request.data.get("OutSum")
    inv_id = request.data.get("InvId")
    received_signature = request.data.get("SignatureValue", "").strip()

    if not out_sum or not inv_id or not received_signature:
        logger.warning(f"[payment_result] Не хватает полей: OutSum={out_sum}, InvId={inv_id}, Signature={received_signature}")
        return Response({"error": "Missing required fields."}, status=status.HTTP_400_BAD_REQUEST)

    if not verify_robokassa_signature(out_sum, inv_id, received_signature):
        logger.warning(f"[payment_result] Неверная подпись для InvId={inv_id}")
        return Response({"error": "Invalid signature."}, status=status.HTTP_400_BAD_REQUEST)

    try:
        payment = Payment.objects.get(inv_id=inv_id)
    except Payment.DoesNotExist:
        logger.error(f"[payment_result] Платёж с InvId={inv_id} не найден")
        return Response({"error": "Payment not found."}, status=status.HTTP_404_NOT_FOUND)

    if payment.status == Payment.Status.SUCCESS:
        logger.info(f"[payment_result] Повторный колбэк: платёж {inv_id} уже успешно обработан")
        return Response(f"OK{inv_id}")

    apply_payment(payment.user, payment.amount)
    payment.status = Payment.Status.SUCCESS
    payment.save()
    logger.info(f"[payment_result] Платёж {inv_id} успешно применён и сохранён")

    notify_payload = {
        "tg_id": payment.user.telegram_id,
        "amount": float(payment.amount),
        "payment_id": inv_id
    }

    try:
        logger.info(f"[payment_result] Отправляем POST-запрос боту: {notify_payload}")
        response = requests.post(
            "http://vpn_bot:8081/notify", 
            json=notify_payload,
            timeout=3
        )
        response.raise_for_status()
        logger.info(f"[payment_result] Бот ответил: {response.status_code} {response.text}")

    except Exception as e:
        logger.error(f"[payment_result] Ошибка при отправке уведомления в бота: {e}")

    return Response(f"OK{inv_id}")


@api_view(["GET", "POST"])
def success_payment(request):
    """Страница при успешной оплате."""
    return HttpResponse("<h1>Оплата прошла успешно! 🎉</h1>")


@api_view(["GET", "POST"])
def fail_payment(request):
    """Страница при ошибке оплаты или отмене."""
    return HttpResponse("<h1>Оплата отменена или ошибка платежа.</h1>")


class CreateCryptoPaymentAPIView(APIView):
    """
    Создание криптоплатежа через Telegram CryptoBot.
    """
    def post(self, request):
        telegram_id = request.data.get("telegram_id")
        amount_rub = request.data.get("amount")
        asset = request.data.get("asset", "TON")

        if not amount_rub:
            return Response({"error": "Поле 'amount' обязательно"}, status=400)

        try:
            amount_rub = Decimal(amount_rub)
            if amount_rub <= 0:
                raise ValueError
        except (InvalidOperation, ValueError):
            return Response({"error": "Неверный формат 'amount'"}, status=400)

        user = VPNUser.objects.filter(telegram_id=telegram_id).first()
        if not user:
            return Response({"error": "Пользователь не найден"}, status=404)

        payment = Payment.objects.create(
            user=user,
            inv_id=generate_unique_inv_id(),
            amount=amount_rub,
            status=Payment.Status.PENDING,
            currency=asset,
        )

        pay_url = generate_crypto_payment_link(payment, asset, amount_rub)
        return Response({"payment_url": pay_url, "inv_id": payment.inv_id})

import logging
logger = logging.getLogger(__name__)

@csrf_exempt
def crypto_webhook(request):
    if request.method != "POST":
        return JsonResponse({"error": "Only POST allowed"}, status=405)

    try:
        logger.info(f"[crypto_webhook] Headers: {dict(request.headers)}")
        logger.info(f"[crypto_webhook] Raw body: {request.body}")

        sign = request.headers.get("sign")
        if not sign:
            return HttpResponseForbidden("Missing signature")

        secret = settings.CRYPTOMUS_API_KEY.encode("utf-8")
        payload = json.loads(request.body.decode("utf-8"))
        normalized_json = json.dumps(payload, separators=(',', ':')).encode("utf-8")
        calculated_sign = hmac.new(secret, normalized_json, hashlib.sha256).hexdigest()

        logger.info(f"[crypto_webhook] Calculated sign: {calculated_sign}")
        logger.info(f"[crypto_webhook] Received sign: {sign}")

        if calculated_sign != sign:
            return HttpResponseForbidden("Invalid signature")

        status = payload.get("status")
        order_id = payload.get("order_id")
        amount = payload.get("amount")
        currency = payload.get("currency")

        if status != "paid":
            return JsonResponse({"ok": True})

        try:
            _, telegram_id, _amount, *_ = order_id.split("_")
            user = VPNUser.objects.get(telegram_id=int(telegram_id))
        except Exception:
            return JsonResponse({"error": "Invalid order_id"}, status=400)

        payment, created = Payment.objects.get_or_create(
            inv_id=payload.get("payment_id"),
            defaults={
                "user": user,
                "amount": Decimal(amount),
                "currency": currency,
                "status": Payment.Status.SUCCESS,
            }
        )

        if not created and payment.status == Payment.Status.SUCCESS:
            return JsonResponse({"ok": True})

        payment.status = Payment.Status.SUCCESS
        payment.save()

        user.balance += Decimal(amount)
        user.save()

        # ⬇️ Уведомление бота
        notify_payload = {
            "tg_id": user.telegram_id,
            "amount": float(amount),
            "payment_id": payload.get("payment_id")
        }

        try:
            logger.info(f"[crypto_webhook] Отправляем POST-запрос боту: {notify_payload}")
            response = requests.post(
                "http://vpn_bot:8081/notify",
                json=notify_payload,
                timeout=3
            )
            response.raise_for_status()
            logger.info(f"[crypto_webhook] Бот ответил: {response.status_code} {response.text}")
        except Exception as e:
            logger.error(f"[crypto_webhook] Ошибка при отправке уведомления в бота: {e}")

        return JsonResponse({"ok": True})

    except Exception as e:
        logger.exception("[crypto_webhook] Общая ошибка")
        return JsonResponse({"error": str(e)}, status=500)


class StarPaymentAPIView(APIView):
    """
    Внутреннее начисление звёзд пользователю.
    """
    def post(self, request):
        user_id = request.data.get("user_id")
        amount = float(request.data.get("amount"))

        user = VPNUser.objects.get(telegram_id=user_id)

        payment = Payment.objects.create(
            user=user,
            inv_id=generate_unique_inv_id(),
            amount=amount,
            status=Payment.Status.SUCCESS,
            currency='Tg stars'
        )

        apply_payment(user, Decimal(amount))

        return Response({
            "message": "OK",
            "amount": amount,
        }, status=status.HTTP_201_CREATED)
