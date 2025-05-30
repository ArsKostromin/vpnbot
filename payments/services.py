# services.py
import hashlib
import requests
from decimal import Decimal, ROUND_HALF_UP
from django.conf import settings
from payments.models import Payment


def generate_unique_inv_id():
    """
    Генерация уникального ID для нового платежа, начиная с 1000.
    """
    last_payment = Payment.objects.order_by('-inv_id').first()
    next_inv_id = (last_payment.inv_id + 1) if last_payment else 1000
    return next_inv_id


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

    # payment.amount всегда в долларах (бот показывает цену в долларах)
    amount_usd = payment.amount

    # Переводим сумму в рубли для Robokassa
    amount_rub = (amount_usd * rate).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    # Сохраняем валюту, если не указана
    if payment.currency.upper() != "USD":
        payment.currency = "USD"
        payment.save(update_fields=["currency"])

    signature_raw = f"{login}:{amount_rub}:{payment.inv_id}:{password1}"
    signature = hashlib.md5(signature_raw.encode('utf-8')).hexdigest()

    base_url = "https://auth.robokassa.ru/Merchant/Index.aspx"
    params = f"MerchantLogin={login}&OutSum={amount_rub}&InvId={payment.inv_id}&SignatureValue={signature}"

    if is_test:
        params += "&IsTest=1"

    return f"{base_url}?{params}"



def verify_robokassa_signature(out_sum: str, inv_id: str, received_signature: str) -> bool:
    """
    Проверка цифровой подписи от Robokassa.
    """
    my_signature_raw = f"{out_sum}:{inv_id}:{settings.ROBOKASSA_PASSWORD2}"
    my_signature = hashlib.md5(my_signature_raw.encode('utf-8')).hexdigest().upper()
    return received_signature.upper() == my_signature
