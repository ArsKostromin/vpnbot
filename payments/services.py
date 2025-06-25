# services.py
import hashlib
import requests
from decimal import Decimal, ROUND_HALF_UP
from django.conf import settings
from payments.models import Payment


def get_usd_to_rub_rate() -> Decimal:
    """
    Получение актуального курса доллара к рублю с сайта ЦБ РФ.
    """
    try:
        response = requests.get('https://www.cbr-xml-daily.ru/daily_json.js', timeout=5)
        response.raise_for_status()
        data = response.json()
        return Decimal(data['Valute']['USD']['Value']).quantize(Decimal('0.01'))
    except Exception:
        # Если курс недоступен — резервный курс
        return Decimal('95.00')


def generate_robokassa_payment_link(payment: Payment) -> str:
    """
    Формирование ссылки для оплаты через Robokassa с пересчётом в рубли.
    Сумма всегда зачисляется на баланс в долларах (payment.amount).
    """
    login = settings.ROBOKASSA_LOGIN
    password1 = settings.ROBOKASSA_PASSWORD1
    is_test = settings.ROBOKASSA_IS_TEST

    rate = get_usd_to_rub_rate()
    amount_usd = payment.amount
    amount_rub = (amount_usd * rate).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    amount_rub_str = format(amount_rub, '.2f')  # всегда две цифры после точки

    if payment.currency.upper() != "USD":
        payment.currency = "USD"
        payment.save(update_fields=["currency"])

    signature_raw = f"{login}:{amount_rub_str}:{payment.id}:{password1}"
    signature = hashlib.md5(signature_raw.encode('utf-8')).hexdigest()

    base_url = "https://auth.robokassa.ru/Merchant/Index.aspx"
    params = f"MerchantLogin={login}&OutSum={amount_rub_str}&InvId={payment.id}&SignatureValue={signature}"

    if is_test:
        params += "&IsTest=1"

    return f"{base_url}?{params}"


def verify_robokassa_signature(out_sum: str, id: str, received_signature: str) -> bool:
    """
    Проверка цифровой подписи от Robokassa.
    """
    my_signature_raw = f"{out_sum}:{id}:{settings.ROBOKASSA_PASSWORD2}"
    my_signature = hashlib.md5(my_signature_raw.encode('utf-8')).hexdigest().upper()
    return received_signature.upper() == my_signature
