#vpn_api/models
from django.db import models
from django.utils import timezone
from dateutil.relativedelta import relativedelta
from user.models import VPNUser

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

    vpn_type = models.CharField(max_length=10, choices=VPN_TYPES)
    duration = models.CharField(max_length=2, choices=DURATION_CHOICES)
    price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.get_vpn_type_display()} ({self.get_duration_display()}) – {self.price}₽"

    class Meta:
        verbose_name_plural = 'Тарифы'
        verbose_name = 'Тариф'

class Subscription(models.Model):
    user = models.ForeignKey(VPNUser, on_delete=models.CASCADE, related_name='subscriptions')
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.CASCADE)
    is_active = models.BooleanField(default=True)
    start_date = models.DateTimeField(default=timezone.now)
    end_date = models.DateTimeField(blank=True, null=True)
    auto_renew = models.BooleanField(default=True)
    paused = models.BooleanField(default=False)

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

    def save(self, *args, **kwargs):
        if not self.end_date:
            self.end_date = self.calculate_end_date()

        if self.end_date and self.end_date < timezone.now():
            self.is_active = False

        super().save(*args, **kwargs)

    class Meta:
        verbose_name_plural = 'Подписки'
        verbose_name = 'Подписку'