from django.db import models
from user.models import VPNUser


class VPNServer(models.Model):
    name = models.CharField(max_length=100)
    ip = models.GenericIPAddressField()
    port = models.PositiveIntegerField()
    protocol = models.CharField(max_length=20, choices=[
        ("vless", "VLESS"),
        ("vmess", "VMESS"),
        ("wireguard", "WireGuard"),
    ])
    limit_per_user = models.PositiveIntegerField(default=1)
    is_active = models.BooleanField(default=True)
    country = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.name} ({self.ip})"


class Tariff(models.Model):
    """
    Тарифный план на VPN-услугу: зависит от типа и длительности.
    """
    VPN_CHOICES = [
        ('mobile', 'Мобильный'),
        ('residential', 'Резидентский'),
        ('rotating', 'С ротацией'),
    ]
    DURATION_CHOICES = [
        ('1m', '1 месяц'),
        ('6m', '6 месяцев'),
        ('12m', '1 год'),
        ('36m', '3 года'),
    ]

    vpn_type = models.CharField(max_length=20, choices=VPN_CHOICES)
    duration = models.CharField(max_length=4, choices=DURATION_CHOICES)
    price_usd = models.DecimalField(max_digits=6, decimal_places=2)

    class Meta:
        unique_together = ('vpn_type', 'duration')

    def __str__(self):
        return f"{self.get_vpn_type_display()} – {self.get_duration_display()} – ${self.price_usd}"


class VPNKey(models.Model):
    """
    Уникальный VLESS/VMESS ключ. Привязан к пользователю и серверу.
    """
    vpn_user = models.ForeignKey(VPNUser, on_delete=models.CASCADE)
    server = models.ForeignKey(VPNServer, on_delete=models.SET_NULL, null=True)
    key = models.CharField(max_length=255, unique=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Key {self.key[:6]}... for {self.vpn_user.telegram_id}"


class Subscription(models.Model):
    """
    Подписка пользователя на услугу VPN. Связана с тарифом и ключом.
    """
    vpn_user = models.ForeignKey(VPNUser, on_delete=models.CASCADE)
    tariff = models.ForeignKey(Tariff, on_delete=models.SET_NULL, null=True)
    vpn_key = models.OneToOneField(VPNKey, on_delete=models.SET_NULL, null=True)
    start_date = models.DateTimeField(auto_now_add=True)
    end_date = models.DateTimeField()
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"Sub: {self.vpn_user.telegram_id} | {self.tariff} | Активна: {self.is_active}"
