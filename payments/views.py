# payments/views.py
import hashlib
from decimal import Decimal, InvalidOperation

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
        return Response({"error": "Missing required fields."}, status=status.HTTP_400_BAD_REQUEST)

    if not verify_robokassa_signature(out_sum, inv_id, received_signature):
        return Response({"error": "Invalid signature."}, status=status.HTTP_400_BAD_REQUEST)

    try:
        payment = Payment.objects.get(inv_id=inv_id)
    except Payment.DoesNotExist:
        return Response({"error": "Payment not found."}, status=status.HTTP_404_NOT_FOUND)

    if payment.status == Payment.Status.SUCCESS:
        return Response(f"OK{inv_id}")

    apply_payment(payment.user, Decimal(out_sum))
    payment.status = Payment.Status.SUCCESS
    payment.save()

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


@api_view(["POST"])
def crypto_webhook(request):
    """
    Обработка webhook-а от CryptoBot об успешной оплате.
    """
    event = request.data
    logger.info(f"[Webhook] Получено событие: {event}")

    if event.get("type") != "invoice_paid":
        logger.warning("[Webhook] Не является событием оплаты")
        return Response({"message": "Not a payment event"}, status=status.HTTP_200_OK)

    payload = event.get("payload")
    if not payload:
        logger.error("[Webhook] Payload отсутствует")
        return Response({"error": "Missing payload"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        inv_id = int(payload)
    except ValueError:
        logger.error(f"[Webhook] Некорректный формат payload: {payload}")
        return Response({"error": "Invalid payload format"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        payment = Payment.objects.get(inv_id=inv_id)
    except Payment.DoesNotExist:
        logger.error(f"[Webhook] Платёж с inv_id={inv_id} не найден")
        return Response({"error": "Payment not found"}, status=status.HTTP_404_NOT_FOUND)

    if payment.status == Payment.Status.SUCCESS:
        logger.info(f"[Webhook] Платёж уже обработан: inv_id={inv_id}")
        return Response({"message": "Already processed"}, status=status.HTTP_200_OK)

    try:
        apply_payment(payment.user, payment.amount)
        payment.status = Payment.Status.SUCCESS
        payment.save()
        logger.info(f"[Webhook] Платёж успешно обработан: inv_id={inv_id}")
        return Response({"message": "Payment processed"}, status=status.HTTP_200_OK)
    except Exception as e:
        logger.exception(f"[Webhook] Ошибка при применении платежа inv_id={inv_id}: {e}")
        return Response({"error": "Internal error"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



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
