#vpn_api/models
from django.db import models
from django.utils import timezone
from dateutil.relativedelta import relativedelta
from user.models import VPNUser
import uuid
from django.conf import settings
from .utils import apply_vless_on_server

class SubscriptionPlan(models.Model):
    VPN_TYPES = [
        ('solo', 'Одиночный VPN'),
        ('double', 'Двойной VPN'),
        ('triple', 'Тройной VPN'),
    ]

    DURATION_CHOICES = [
        ('1m', '1 месяц'),
        ('6m', '6 месяцев'),
        ('1y', '1 год'),
        ('3y', '3 года'),
    ]

    vpn_type = models.CharField(max_length=10, choices=VPN_TYPES, verbose_name='Тип впн')
    duration = models.CharField(max_length=2, choices=DURATION_CHOICES, verbose_name='Длительность')
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Цена')

    def __str__(self):
        return f"{self.get_vpn_type_display()} ({self.get_duration_display()}) – {self.price}₽"

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

    def calculate_end_date(self):
        duration_map = {
            '1m': relativedelta(months=1),
            '6m': relativedelta(months=6),
            '1y': relativedelta(years=1),
            '3y': relativedelta(years=3),
        }
        duration = duration_map.get(self.plan.duration)
        if duration is None:
            raise ValueError(f"Unknown plan duration: {self.plan.duration}")
        return self.start_date + duration
    
    
    @staticmethod
    def generate_vless_config(user_uuid, ip, port=80, path="/vless", tag="AnonixVPN"):
        return f"vless://{user_uuid}@{ip}:{port}?encryption=none&type=ws&security=none&path={path}#{tag}"


    def save(self, *args, **kwargs):
        if not self.end_date:
            self.end_date = self.calculate_end_date()

        if self.end_date and self.end_date < timezone.now():
            self.is_active = False

        # Генерация UUID, если еще не задан
        if not self.vless:
            user_uuid = str(uuid.uuid4())
            self.vless = self.generate_vless_config(
                user_uuid=user_uuid,
                ip=settings.SERVER_IP  # Задай IP в settings.py, например: SERVER_IP = "159.198.77.222"
            )
            # Обновить конфиг на сервере:
            apply_vless_on_server(user_uuid)

        super().save(*args, **kwargs)

    class Meta:
        verbose_name_plural = 'Подписки'
        verbose_name = 'Подписку'
        
