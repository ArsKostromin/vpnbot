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
        logger.warning(f"[payment_result] Повторный колбэк: платёж {inv_id} уже успешно обработан")
        return Response(f"OK{inv_id}")

    apply_payment(payment.user, payment.amount)
    payment.status = Payment.Status.SUCCESS
    payment.save()
    logger.warning(f"[payment_result] Платёж {inv_id} успешно применён и сохранён")

    notify_payload = {
        "tg_id": payment.user.telegram_id,
        "amount": float(payment.amount),
        "payment_id": inv_id
    }

    try:
        logger.warning(f"[payment_result] Отправляем POST-запрос боту: {notify_payload}")
        response = requests.post(
            "http://vpn_bot:8081/notify", 
            json=notify_payload,
            timeout=3
        )
        response.raise_for_status()
        logger.warning(f"[payment_result] Бот ответил: {response.status_code} {response.text}")

    except Exception as e:
        logger.error(f"[payment_result] Ошибка при отправке уведомления в бота: {e}")

    return Response(f"OK{inv_id}")

@api_view(["GET", "POST"])
def success_payment(request):
    """Закрывает окно после успешной оплаты."""
    return HttpResponse("""
        <html>
            <head>
                <title>Ошибка оплаты</title>
                <style>
                    body { display: flex; flex-direction: column; justify-content: center; align-items: center; height: 100vh; margin: 0; }
                    h1, p { text-align: center; }
                </style>
                <script>
                    window.onload = function() {
                        window.close();
                        setTimeout(() => {
                            window.location.href = 'https://t.me/Anonixvpn_vpnBot'; // fallback
                        }, 1000);
                    }
                </script>
            </head>
            <body>
                <h1>Оплата отменена или произошла ошибка.</h1>
                <p>Вы будете перенаправлены...</p>
            </body>
        </html>
    """)

@api_view(["GET", "POST"])
def fail_payment(request):
    """Закрывает окно при ошибке/отмене."""
    return HttpResponse("""
        <html>
            <head>
                <title>Ошибка оплаты</title>
                <script>
                    window.onload = function() {
                        window.close();
                        setTimeout(() => {
                            window.location.href = 'https://t.me/Anonixvpn_vpnBot'; // fallback
                        }, 1000);
                    }
                </script>
            </head>
            <body>
                <h1>Оплата отменена или произошла ошибка.</h1>
                <p>Вы будете перенаправлены...</p>
            </body>
        </html>
    """)

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
    logger.warning("🟡 Вызов /api/crypto/webhook/")
    logger.warning(f"📨 Method: {request.method}")
    logger.warning(f"📨 Headers: {dict(request.headers)}")

    if request.method != "POST":
        logger.warning("🔴 Метод не POST")
        return JsonResponse({"error": "Only POST allowed"}, status=405)

    try:
        raw = request.body.decode("utf-8", errors="replace")
        logger.warning(f"📦 Raw body: {raw}")

        data = json.loads(raw)
        logger.warning(f"✅ JSON payload: {data}")

        order_id = data.get("order_id")
        amount = data.get("amount")
        status = data.get("status")
        currency = data.get("currency")

        logger.warning(f"💰 Статус: {status}, Order ID: {order_id}, Amount: {amount}, Currency: {currency}")

        if status not in ("paid", "paid_over"):
            logger.warning("ℹ️ Статус не 'paid', игнорим")
            return JsonResponse({"ok": True})

        # Извлекаем telegram_id
        try:
            _, telegram_id, *_ = order_id.split("_")
            logger.warning(f"👤 telegram_id: {telegram_id}")
        except Exception as e:
            logger.warning(f"❌ Не удалось достать telegram_id: {e}")
            return JsonResponse({"error": "Invalid order_id"}, status=400)

        user = VPNUser.objects.get(telegram_id=int(telegram_id))
        user.balance += Decimal(amount)
        user.save()

        logger.warning(f"💸 Баланс пополнен: {user.balance}")

        # Отправка уведомления боту
        notify_payload = {
            "tg_id": user.telegram_id,
            "amount": float(amount),
        }

        try:
            logger.warning(f"📤 Отправка уведомления: {notify_payload}")
            response = requests.post(
                "http://vpn_bot:8081/notify",
                json=notify_payload,
                timeout=3
            )
            logger.warning(f"✅ Ответ от бота: {response.status_code} {response.text}")
        except Exception as e:
            logger.warning(f"❌ Ошибка при уведомлении бота: {e}")

        return JsonResponse({"ok": True})

    except Exception as e:
        logger.exception("💥 Ошибка при обработке webhook")
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