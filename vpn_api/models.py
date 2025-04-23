from django.db import models

# Create your models here.
class Server(models.Model):
    name = models.CharField(max_length=100)
    ip = models.GenericIPAddressField()
    port = models.PositiveIntegerField()
    protocol = models.CharField(max_length=20, choices=[
        ("vless", "VLESS"),
        ("vmess", "VMESS"),
        ("wireguard", "WireGuard"),
    ])
    limit_per_user = models.PositiveIntegerField(default=1)  # 1 ключ на пользователя
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} ({self.ip})"
