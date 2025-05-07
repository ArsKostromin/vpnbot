from django.db import models
from django.utils import timezone
from user.models import VPNUser
from vpn_api.models import SubscriptionPlan

class Coupon(models.Model):
    TYPE_CHOICES = [
        ('balance', 'Пополнение баланса'),
        ('subscription', 'Подарочная подписка'),
    ]

    VPN_USAGE_CHOICES = [
        ('youtube', 'YouTube'),
        ('torrents', 'Торренты'),
        ('social', 'Соцсети'),
        ('gaming', 'Игры'),
        ('streaming', 'Стриминг'),
    ]

    DURATION_CHOICES = [
        ('1m', '1 месяц'),
        ('6m', '6 месяцев'),
        ('1y', '1 год'),
        ('3y', '3 года'),
    ]

    code = models.CharField(max_length=20, unique=True, verbose_name="Промокод")
    type = models.CharField(max_length=20, choices=TYPE_CHOICES, verbose_name='Тип промокода')
    expiration_date = models.DateTimeField(verbose_name='Действует до')
    is_used = models.BooleanField(default=False, verbose_name='Использован')
    used_by = models.ForeignKey(
        VPNUser, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='used_coupons', verbose_name='Использовавший'
    )

    discount_amount = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True, verbose_name='Сумма пополнения'
    )

    vpn_usage = models.CharField(
        max_length=20, choices=VPN_USAGE_CHOICES, null=True, blank=True, verbose_name='Назначение VPN'
    )
    duration = models.CharField(max_length=3, choices=DURATION_CHOICES, null=True, blank=True, verbose_name='Срок')

    def __str__(self):
        return f"{self.code} ({self.type})"

    class Meta:
        verbose_name = 'Купон'
        verbose_name_plural = 'Купоны'
