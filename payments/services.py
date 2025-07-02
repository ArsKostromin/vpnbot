# services.py
import hashlib
import requests
from decimal import Decimal, ROUND_HALF_UP
from django.conf import settings
from payments.models import Payment
import logging

logger = logging.getLogger(__name__)


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

    description = "Подписка на VPN"
    culture = "ru"
    email = getattr(payment.user, "email", "")
    shp_userid = payment.user.id if hasattr(payment.user, "id") else ""
    params = (
        f"MerchantLogin={login}"
        f"&OutSum={amount_rub_str}"
        f"&InvId={payment.id}"
        f"&Description={description}"
        f"&SignatureValue={signature}"
        f"&Recurring=True"
        f"&RecurringType=auto"
        f"&Culture={culture}"
    )
    if email:
        params += f"&Email={email}"
    if shp_userid:
        params += f"&Shp_userid={shp_userid}"
    if is_test:
        params += "&IsTest=1"

    base_url = "https://auth.robokassa.ru/Merchant/Index.aspx"

    return f"{base_url}?{params}"


def verify_robokassa_signature(out_sum: str, id: str, received_signature: str) -> bool:
    """
    Проверка цифровой подписи от Robokassa.
    """
    my_signature_raw = f"{out_sum}:{id}:{settings.ROBOKASSA_PASSWORD2}"
    my_signature = hashlib.md5(my_signature_raw.encode('utf-8')).hexdigest().upper()
    return received_signature.upper() == my_signature


def robokassa_recurring_charge(user, amount_rub):
    """
    Пытается списать сумму с карты пользователя через Robokassa по recurring_id.
    Возвращает True при успехе, иначе False.
    """
    recurring_id = getattr(user, 'robokassa_recurring_id', None)
    if not recurring_id:
        logger.warning(f"[robokassa_recurring_charge] Нет recurring_id для пользователя {user.telegram_id}")
        return False

    try:
        # Создаём новый платёж для дочернего списания
        child_payment = Payment.objects.create(
            user=user,
            amount=Decimal(str(amount_rub)),
            status=Payment.Status.PENDING,
            currency='Рубли'
        )
        
        # Формируем данные для дочернего платежа согласно документации
        data = {
            "MerchantLogin": settings.ROBOKASSA_LOGIN,
            "InvoiceID": child_payment.id,  # Новый ID для дочернего платежа
            "PreviousInvoiceID": recurring_id,  # ID материнского платежа
            "Description": "Автопополнение баланса VPN",
            "OutSum": str(amount_rub),
            "SignatureValue": hashlib.md5(
                f"{settings.ROBOKASSA_LOGIN}:{amount_rub}:{child_payment.id}:{settings.ROBOKASSA_PASSWORD1}".encode('utf-8')
            ).hexdigest()
        }
        
        # Отправляем запрос на специальный URL для рекуррентных платежей
        response = requests.post("https://auth.robokassa.ru/Merchant/Recurring", data=data, timeout=10)
        logger.warning(f"[robokassa_recurring_charge] Ответ Robokassa: {response.status_code} {response.text}")
        
        if response.status_code == 200 and "OK" in response.text.upper():
            logger.warning(f"[robokassa_recurring_charge] Успешное автосписание для пользователя {user.telegram_id}")
            # Обновляем статус платежа
            child_payment.status = Payment.Status.SUCCESS
            child_payment.save()
            return True
        else:
            logger.warning(f"[robokassa_recurring_charge] Не удалось списать с карты: {response.text}")
            # Обновляем статус платежа на неуспешный
            child_payment.status = Payment.Status.FAILED
            child_payment.save()
            return False
    except Exception as e:
        logger.warning(f"[robokassa_recurring_charge] Ошибка при автосписании: {e}")
        return False
