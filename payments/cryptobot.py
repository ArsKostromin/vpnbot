# payments/cryptobot.py
import requests
from django.conf import settings
from user.models import VPNUser
from payments.models import Payment
import logging
from decimal import Decimal

CRYPTOPAY_API_URL = "https://pay.crypt.bot/api"

def generate_crypto_payment_link(payment: Payment, asset: str, amount_rub: Decimal):
    print("amount_rub:", amount_rub, type(amount_rub))

    headers = {
        "Crypto-Pay-API-Token": settings.CRYPTOPAY_API_TOKEN,
    }
    data = {
        "currency_type": "fiat",
        "fiat": "RUB",
        "amount": str(amount_rub),
        "accepted_assets": asset,
        "description": f"Пополнение баланса для {payment.user.telegram_id}",
        "payload": str(payment.inv_id),
    }
    print("DEBUG data to CryptoBot:", data)

    response = requests.post(f"{CRYPTOPAY_API_URL}/createInvoice", headers=headers, json=data)
    if response.status_code != 200:
        raise Exception(f"CryptoBot error: {response.text}")

    return response.json()["result"]["bot_invoice_url"]


