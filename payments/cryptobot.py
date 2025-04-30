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


# Функция get_crypto_rub_rate больше не нужна, но оставим её, если пригодится в будущем
def get_crypto_rub_rate(asset: str) -> float:
    try:
        symbol_map = {
            "TON": "toncoin",
            "USDT": "tether",
            "BTC": "bitcoin",
        }
        coingecko_id = symbol_map.get(asset.upper())
        if not coingecko_id:
            return None

        response = requests.get(
            "https://api.coingecko.com/api/v3/simple/price",
            params={"ids": coingecko_id, "vs_currencies": "rub"},
            timeout=5
        )
        return response.json()[coingecko_id]["rub"]
    except Exception as e:
        logging.error(f"Ошибка получения курса {asset} к RUB: {e}")
        return None