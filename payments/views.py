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
from django.utils import timezone

from user.models import VPNUser
from payments.models import Payment
from payments.cryptobot import generate_crypto_payment_link
from payments.utils import apply_payment
from payments.services import (
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
        amount = float(amount)
    except (ValueError, TypeError):
        return Response({"error": "Некорректная сумма."}, status=status.HTTP_400_BAD_REQUEST)

    user = VPNUser.objects.get(telegram_id=telegram_id)

    payment = Payment.objects.create(
        user=user,
        amount=Decimal(str(amount)),
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
    # Логируем ВСЁ тело запроса и параметры
    logger.warning(f"[payment_result] request.data: {dict(request.data)}")
    logger.warning(f"[payment_result] request.POST: {dict(request.POST)}")
    logger.warning(f"[payment_result] request.GET: {dict(request.GET)}")
    logger.warning(f"[payment_result] request.META: {request.META}")
    out_sum = request.data.get("OutSum")
    id = request.data.get("InvId")
    received_signature = request.data.get("SignatureValue", "").strip()

    if not out_sum or not id or not received_signature:
        logger.warning(f"[payment_result] Не хватает полей: OutSum={out_sum}, id={id}, Signature={received_signature}")
        return Response({"error": "Missing required fields."}, status=status.HTTP_400_BAD_REQUEST)

    if not verify_robokassa_signature(out_sum, id, received_signature):
        logger.warning(f"[payment_result] Неверная подпись для id={id}")
        return Response({"error": "Invalid signature."}, status=status.HTTP_400_BAD_REQUEST)

    try:
        payment = Payment.objects.get(id=id)
    except Payment.DoesNotExist:
        logger.error(f"[payment_result] Платёж с id={id} не найден")
        return Response({"error": "Payment not found."}, status=status.HTTP_404_NOT_FOUND)

    if payment.status == Payment.Status.SUCCESS:
        logger.warning(f"[payment_result] Повторный колбэк: платёж {id} уже успешно обработан")
        return Response(f"OK{id}")

    apply_payment(payment.user, payment.amount)
    payment.status = Payment.Status.SUCCESS
    payment.save()
    logger.warning(f"[payment_result] Платёж {id} успешно применён и сохранён")

    # --- АВТОПРОДЛЕНИЕ ПОДПИСКИ ПОСЛЕ АВТОСПИСАНИЯ ---
    from vpn_api.models import Subscription
    from vpn_api.utils import create_vless, get_duration_delta
    from vpn_api.services import get_least_loaded_server, get_least_loaded_server_by_country
    from django.utils import timezone
    from uuid import uuid4

    # Проверяем, что это автосписание (есть recurring_id и нет обычного платежа)
    is_recurring = payment.user.robokassa_recurring_id and payment.id != int(payment.user.robokassa_recurring_id)
    if is_recurring:
        # Ищем истёкшую подписку с auto_renew
        expired_sub = Subscription.objects.filter(user=payment.user, is_active=False, auto_renew=True).order_by('-end_date').first()
        if expired_sub and expired_sub.plan:
            plan = expired_sub.plan
            price = plan.get_current_price()
            if payment.user.balance >= price:
                # Выбор сервера
                if plan.vpn_type == "country":
                    server = expired_sub.server or get_least_loaded_server()
                else:
                    server = get_least_loaded_server()
                if server:
                    user_uuid = uuid4()
                    vless_result = create_vless(server, user_uuid)
                    if vless_result["success"]:
                        delta = get_duration_delta(plan.duration)
                        start_date = timezone.now()
                        end_date = start_date + delta
                        Subscription.objects.create(
                            user=payment.user,
                            plan=plan,
                            start_date=start_date,
                            end_date=end_date,
                            vless=vless_result["vless_link"],
                            uuid=user_uuid,
                            server=server,
                            auto_renew=True
                        )
                        payment.user.balance -= price
                        payment.user.save()
                        logger.warning(f"[auto_renew] Подписка успешно продлена после автосписания для пользователя {payment.user.telegram_id}")
                    else:
                        logger.warning(f"[auto_renew] Ошибка создания VLESS: {vless_result}")
                else:
                    logger.warning(f"[auto_renew] Нет доступных серверов для автопродления!")
            else:
                logger.warning(f"[auto_renew] Недостаточно средств для автопродления после автосписания!")
        else:
            logger.warning(f"[auto_renew] Не найдена истёкшая подписка с auto_renew для пользователя {payment.user.telegram_id}")
    # --- конец блока автопродления ---

    # --- Сохраняем recurring_id, если Robokassa его вернула ---
    # Для рекуррентных платежей Robokassa возвращает ID материнского платежа
    # который нужно использовать как PreviousInvoiceID в дочерних платежах
    recurring_id = request.data.get("InvoiceID") or request.data.get("InvId")
    if recurring_id:
        payment.user.robokassa_recurring_id = recurring_id
        payment.user.save(update_fields=["robokassa_recurring_id"])
        logger.warning(f"[payment_result] Сохранён Robokassa Recurring ID для пользователя {payment.user.telegram_id}: {recurring_id}")
    else:
        # Если RecurringID не пришёл, но платёж был с параметром Recurring=true,
        # то используем ID текущего платежа как материнский
        if "Recurring=true" in request.get_full_path() or request.data.get("Recurring") == "true":
            payment.user.robokassa_recurring_id = str(payment.id)
            payment.user.save(update_fields=["robokassa_recurring_id"])
            logger.warning(f"[payment_result] Сохранён ID материнского платежа для пользователя {payment.user.telegram_id}: {payment.id}")
        else:
            logger.warning(f"[payment_result] Recurring ID не получен для пользователя {payment.user.telegram_id}")
    # --- конец блока recurring_id ---

    notify_payload = {
        "tg_id": payment.user.telegram_id,
        "amount": float(payment.amount),
        "payment_id": payment.id
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

    return Response(f"OK{payment.id}")

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
            amount=amount_rub,
            status=Payment.Status.PENDING,
            currency=asset,
        )

        pay_url = generate_crypto_payment_link(payment, asset, amount_rub)
        return Response({"payment_url": pay_url, "inv_id": payment.id})

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
            amount=amount,
            status=Payment.Status.SUCCESS,
            currency='Tg stars'
        )

        apply_payment(user, Decimal(amount))

        return Response({
            "message": "OK",
            "amount": amount,
        }, status=status.HTTP_201_CREATED)