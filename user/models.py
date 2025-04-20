from django.db import models

VPN_CHOICES = [
    ('single', 'Одиночный VPN'),
    ('double', 'Двойной VPN'),
    ('triple', 'Тройной VPN'),
]

class VPNUser(models.Model):
    telegram_id = models.BigIntegerField(unique=True)
    vpn_key = models.TextField(null=True, blank=True) # для активаций в приложений
    created_at = models.DateTimeField(auto_now_add=True)
    current_ip = models.GenericIPAddressField(null=True, blank=True)
    vpn_type = models.CharField(max_length=20, choices=VPN_CHOICES, default='single')

    def __str__(self):
        return f"VPNUser {self.telegram_id} ({self.vpn_type})"
