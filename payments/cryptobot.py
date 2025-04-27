# payments/cryptobot.py
import requests
from decimal import Decimal
from django.conf import settings
from user.models import VPNUser
from payments.models import Payment

CRYPTOPAY_API_URL = "https://pay.crypt.bot/api"

def generate_crypto_payment_link(payment: Payment):
    headers = {
        "Crypto-Pay-API-Token": settings.CRYPTOPAY_API_TOKEN,
    }
    data = {
        "asset": "TON",  # Можно заменить на USDT, BTC и т.д.
        "amount": float(payment.amount),
        "payment_id": payment.inv_id,  # передадим id платежа для связи
        "description": f"Пополнение баланса для {payment.user.telegram_id}",
    }
    response = requests.post(f"{CRYPTOPAY_API_URL}/createInvoice", headers=headers, json=data)

    if response.status_code != 200:
        raise Exception(f"CryptoBot error: {response.text}")

    invoice_url = response.json()["result"]["pay_url"]
    return invoice_url
