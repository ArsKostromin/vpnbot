from django.db import models
from django.utils import timezone
from dateutil.relativedelta import relativedelta
from user.models import VPNUser
import uuid
from django.conf import settings
import urllib.parse

class SubscriptionPlan(models.Model):
    VPN_TYPES = [
        ('socials', 'для соц.сетей'),
        ('torrents', 'Для загрузки файлов'),
        ('secure', '🛡 Двойное шифрование'),
        ('country', '🌐 Выбор по стране'),
        ("serfing", 'Для серфинга')
    ]

    DURATION_CHOICES = [
        ('1m', '1 месяц'),
        ('3m', '3 месяца'),
        ('6m', '6 месяца'),
        ('1y', '1 год'),
    ]

    vpn_type = models.CharField(max_length=10, choices=VPN_TYPES, verbose_name='Тип впн')
    duration = models.CharField(max_length=2, choices=DURATION_CHOICES, verbose_name='Длительность')
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Цена')

    discount_active = models.BooleanField(default=False, verbose_name="Скидка активна")
    discount_percent = models.PositiveIntegerField(default=0, verbose_name="Скидка в %")
    discount_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="Цена со скидкой")
    discount_text = models.CharField(max_length=255, null=True, blank=True, verbose_name="Текст скидки (для отображения в боте)")

    def get_current_price(self):
        if self.discount_active and self.discount_price:
            return self.discount_price
        return self.price

    def get_display_price(self, with_discount=True):
        if self.discount_active and self.discount_price and with_discount:
            return f"~{self.price}₽~ {self.discount_price}₽"
        return f"{self.price}₽"

    def save(self, *args, **kwargs):
        if self.discount_active and self.discount_percent > 0:
            self.discount_price = round(self.price * (100 - self.discount_percent) / 100, 2)
        else:
            self.discount_price = None
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.get_vpn_type_display()} ({self.get_duration_display()}) – {self.get_display_price()}"

    class Meta:
        verbose_name_plural = 'Тарифы'
        verbose_name = 'Тариф'

class Subscription(models.Model):
    user = models.ForeignKey(VPNUser, on_delete=models.CASCADE, related_name='subscriptions', verbose_name='Пользователь')
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.CASCADE, verbose_name='План')
    is_active = models.BooleanField(default=True, verbose_name='Активна')
    start_date = models.DateTimeField(default=timezone.now, verbose_name='Дата начала')
    end_date = models.DateTimeField(blank=True, null=True, verbose_name='Дата окончания')
    auto_renew = models.BooleanField(default=True, verbose_name='Автопродление')
    paused = models.BooleanField(default=False, verbose_name='Пауза')
    vless = models.TextField(blank=True, null=True, verbose_name='VLESS конфиг')
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, verbose_name="UUID", blank=True, null=True)

    def calculate_end_date(self):
        duration_map = {
            '1m': relativedelta(months=1),
            '3m': relativedelta(months=3),
            '6m': relativedelta(months=6),
            '1y': relativedelta(years=1),
        }
        duration = duration_map.get(self.plan.duration)
        if duration is None:
            raise ValueError(f"Unknown plan duration: {self.plan.duration}")
        return self.start_date + duration

    def save(self, *args, **kwargs):
        if not self.end_date:
            self.end_date = self.calculate_end_date()

        if self.end_date and self.end_date < timezone.now():
            self.is_active = False

        super().save(*args, **kwargs)

    class Meta:
        verbose_name_plural = 'Подписки'
        verbose_name = 'Подписку'


class VPNServer(models.Model):
    country = models.CharField(max_length=50, verbose_name="Страна")  # просто текстом, типа '🇺🇸 США'
    name = models.CharField(max_length=100, verbose_name="Название (например, us1)")
    domain = models.CharField(max_length=255, verbose_name="Домен (например, us1.anonixvpn.space)")
    api_url = models.URLField(verbose_name="FastAPI URL (https://domain/api)")
    is_active = models.BooleanField(default=True, verbose_name="Активен")

    def __str__(self):
        return f"{self.country} — {self.name}"