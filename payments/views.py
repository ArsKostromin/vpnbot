#payments/views
import hashlib
from decimal import Decimal
from django.conf import settings
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.http import HttpResponse

from user.models import VPNUser
from payments.models import Payment
import uuid  # для генерации уникального inv_id

from payments.cryptobot import generate_crypto_payment_link, get_crypto_rub_rate
from payments.models import Payment
from rest_framework.views import APIView
import requests

ALLOWED_AMOUNTS = [1, 100, 500]

def generate_robokassa_payment_link(payment: Payment):
    login = settings.ROBOKASSA_LOGIN
    password1 = settings.ROBOKASSA_PASSWORD1
    is_test = settings.ROBOKASSA_IS_TEST

    signature_raw = f"{login}:{payment.amount}:{payment.inv_id}:{password1}"
    signature = hashlib.md5(signature_raw.encode('utf-8')).hexdigest()

    base_url = "https://auth.robokassa.ru/Merchant/Index.aspx"
    params = f"MerchantLogin={login}&OutSum={payment.amount}&InvId={payment.inv_id}&SignatureValue={signature}"

    if is_test:
        params += "&IsTest=1"

    return f"{base_url}?{params}"


@api_view(["POST"])
def create_payment(request):
    telegram_id = request.data.get("telegram_id")
    amount = request.data.get("amount")

    if not telegram_id:
        return Response({"error": "telegram_id is required"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        amount = int(amount)
    except (ValueError, TypeError):
        return Response({"error": "Некорректная сумма."}, status=status.HTTP_400_BAD_REQUEST)

    if amount not in ALLOWED_AMOUNTS:
        return Response({"error": f"Можно выбрать только {ALLOWED_AMOUNTS} ₽."}, status=status.HTTP_400_BAD_REQUEST)

    user = VPNUser.objects.get(telegram_id=telegram_id)

    # Генерация уникального InvId
    last_payment = Payment.objects.order_by('-inv_id').first()
    next_inv_id = (last_payment.inv_id + 1) if last_payment else 1000  # начинаем с 1000

    # Создаём запись платежа
    payment = Payment.objects.create(
        user=user,
        inv_id=next_inv_id,
        amount=Decimal(amount),
        status=Payment.Status.PENDING
    )

    payment_link = generate_robokassa_payment_link(payment)

    return Response({
        "payment_url": payment_link
    })


@api_view(["POST"])
def payment_result(request):
    out_sum = request.data.get("OutSum")
    inv_id = request.data.get("InvId")
    received_signature = request.data.get("SignatureValue", "").strip()

    if not out_sum or not inv_id or not received_signature:
        return Response({"error": "Missing required fields."}, status=status.HTTP_400_BAD_REQUEST)

    my_signature_raw = f"{out_sum}:{inv_id}:{settings.ROBOKASSA_PASSWORD2}"
    my_signature = hashlib.md5(my_signature_raw.encode('utf-8')).hexdigest().upper()

    if received_signature.upper() != my_signature:
        return Response({"error": "Invalid signature."}, status=status.HTTP_400_BAD_REQUEST)

    try:
        payment = Payment.objects.get(inv_id=inv_id)
    except Payment.DoesNotExist:
        return Response({"error": "Payment not found."}, status=status.HTTP_404_NOT_FOUND)

    if payment.status == Payment.Status.SUCCESS:
        return Response(f"OK{inv_id}")  # уже обработан

    # Обновляем баланс пользователя
    user = payment.user
    user.balance += Decimal(out_sum)
    user.save()

    # Обновляем статус платежа
    payment.status = Payment.Status.SUCCESS
    payment.save()

    return Response(f"OK{inv_id}")


@api_view(["GET", "POST"])
def success_payment(request):
    return HttpResponse("<h1>Оплата прошла успешно! 🎉</h1>")

@api_view(["GET", "POST"])
def fail_payment(request):
    return HttpResponse("<h1>Оплата отменена или ошибка платежа.</h1>")



#крипта
from decimal import Decimal, InvalidOperation

class CreateCryptoPaymentAPIView(APIView):
    def post(self, request):
        telegram_id = request.data.get("telegram_id")
        amount_rub = request.data.get("amount")
        asset = request.data.get("asset", "TON")
        print("amount_rub:", amount_rub, type(amount_rub))

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

        last_payment = Payment.objects.order_by('-inv_id').first()
        next_inv_id = (last_payment.inv_id + 1) if last_payment else 1000

        payment = Payment.objects.create(
            user=user,
            inv_id=next_inv_id,
            amount=amount_rub,
            status=Payment.Status.PENDING,
            currency=asset,
        )

        pay_url = generate_crypto_payment_link(payment, asset, amount_rub)
        return Response({"payment_url": pay_url, "inv_id": next_inv_id})



@api_view(["POST"])
def crypto_webhook(request):
    event = request.data

    if event.get("type") != "invoice_paid":
        return Response({"message": "Not a payment event"}, status=status.HTTP_200_OK)

    payload = event.get("payload")
    if not payload:
        return Response({"error": "Missing payload"}, status=status.HTTP_400_BAD_REQUEST)

    inv_id = payload.get("payment_id")
    amount = Decimal(payload.get("amount", 0))

    try:
        payment = Payment.objects.get(inv_id=inv_id)
    except Payment.DoesNotExist:
        return Response({"error": "Payment not found"}, status=status.HTTP_404_NOT_FOUND)

    if payment.status == Payment.Status.SUCCESS:
        return Response({"message": "Already processed"}, status=status.HTTP_200_OK)

    user = payment.user
    user.balance += amount
    user.save()

    payment.status = Payment.Status.SUCCESS
    payment.save()

    return Response({"message": "Payment processed"}, status=status.HTTP_200_OK)