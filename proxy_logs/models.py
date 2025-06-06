# vpn_api/models.py
from user.models import VPNUser
from django.db import models

class ProxyLog(models.Model):
    user = models.ForeignKey(VPNUser, on_delete=models.CASCADE, null=True, blank=True, related_name='proxy_logs', verbose_name='Пользователь')
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name="Дата и время записи")
    raw_log = models.TextField(verbose_name="Исходный лог")
    remote_ip = models.GenericIPAddressField(null=True, blank=True, verbose_name="IP-адрес клиента")
    domain = models.CharField(max_length=255, null=True, blank=True, verbose_name="Домен")
    status = models.CharField(max_length=32, null=True, blank=True, verbose_name="Статус")
    bytes_sent = models.IntegerField(null=True, blank=True, verbose_name="Отправлено байт")

    def __str__(self):
        return f"{self.timestamp} - {self.domain or 'нет домена'}"

    class Meta:
        verbose_name = 'лог'
        verbose_name_plural = 'логи'