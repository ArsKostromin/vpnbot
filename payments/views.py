# payments/views.py
import hashlib
from decimal import Decimal, InvalidOperation
from django.conf import settings
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.http import HttpResponse
from rest_framework.views import APIView

from user.models import VPNUser
from payments.models import Payment
from payments.cryptobot import generate_crypto_payment_link
from payments.utils import apply_payment


def generate_unique_inv_id():
    last_payment = Payment.objects.order_by('-inv_id').first()
    next_inv_id = (last_payment.inv_id + 1) if last_payment else 1000
    return next_inv_id


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

    payment = Payment.objects.create(
        user=user,
        inv_id=generate_unique_inv_id(),
        amount=Decimal(amount),
        status=Payment.Status.PENDING,
        currency='Рубли'
    )

    payment_link = generate_robokassa_payment_link(payment)

    return Response({"payment_url": payment_link})


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
        return Response(f"OK{inv_id}")

    apply_payment(payment.user, Decimal(out_sum))
    payment.status = Payment.Status.SUCCESS
    payment.save()

    return Response(f"OK{inv_id}")


@api_view(["GET", "POST"])
def success_payment(request):
    return HttpResponse("<h1>Оплата прошла успешно! 🎉</h1>")


@api_view(["GET", "POST"])
def fail_payment(request):
    return HttpResponse("<h1>Оплата отменена или ошибка платежа.</h1>")


class CreateCryptoPaymentAPIView(APIView):
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

    apply_payment(payment.user, amount)
    payment.status = Payment.Status.SUCCESS
    payment.save()

    return Response({"message": "Payment processed"}, status=status.HTTP_200_OK)


class StarPaymentAPIView(APIView):
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
