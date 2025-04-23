from django.db import models
import uuid

VPN_CHOICES = [
    ('single', 'Одиночный VPN'),
    ('double', 'Двойной VPN'),
    ('triple', 'Тройной VPN'),
]

class VPNUser(models.Model):
    telegram_id = models.BigIntegerField(unique=True)
    username = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    current_ip = models.GenericIPAddressField(null=True, blank=True)
    vpn_type = models.CharField(max_length=20, choices=VPN_CHOICES, default='single')
    referred_by  = models.UUIDField(default=uuid.uuid4, unique=True,
                          primary_key=True, editable=False) # для активаций в приложений

    def __str__(self):
        return f"VPNUser {self.telegram_id} ({self.vpn_type})"
