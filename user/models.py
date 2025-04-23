from django.db import models
import uuid


class VPNUser(models.Model):
    telegram_id = models.BigIntegerField(unique=True)
    username = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    current_ip = models.GenericIPAddressField(null=True, blank=True)
    referred_by = models.UUIDField(default=uuid.uuid4, unique=True)
    balance = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    is_banned = models.BooleanField(default=False)

    def __str__(self):
        return f"VPNUser {self.telegram_id}"
