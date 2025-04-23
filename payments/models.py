from django.db import models
from user.models import VPNUser
from vpn_api.models import Tariff
import uuid


class PaymentMethod(models.Model):
    """
    Платёжная система (например, ЮMoney, USDT, CryptoBot, Qiwi и т.д.)
    """
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=50, unique=True)  # 'qiwi', 'usdt_trc20', 'yoomoney'
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class Transaction(models.Model):
    """
    Транзакция пополнения или списания.
    """
    TRANSACTION_TYPES = [
        ('topup', 'Пополнение'),
        ('purchase', 'Покупка'),
        ('refund', 'Возврат'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(VPNUser, on_delete=models.CASCADE)
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPES)
    amount = models.DecimalField(max_digits=8, decimal_places=2)
    payment_method = models.ForeignKey(PaymentMethod, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.get_transaction_type_display()} {self.amount} for {self.user.telegram_id}"


class PaymentSession(models.Model):
    """
    Временная запись о намерении оплаты (например, с CryptoBot/ЮMoney), ожидание callback'а.
    """
    user = models.ForeignKey(VPNUser, on_delete=models.CASCADE)
    payment_method = models.ForeignKey(PaymentMethod, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=8, decimal_places=2)
    is_confirmed = models.BooleanField(default=False)
    external_payment_id = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Pending {self.amount} via {self.payment_method.code} for {self.user.telegram_id}"
