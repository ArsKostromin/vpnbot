from django.db import models
from user.models import VPNUser

class Payment(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', 'В ожидании'
        SUCCESS = 'success', 'Успешно'
        FAIL = 'fail', 'Ошибка'

    user = models.ForeignKey(VPNUser, on_delete=models.CASCADE, related_name='payments', verbose_name='Пользователь')
    amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Стоимость пополнения')
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING, verbose_name='Статус')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    currency = models.CharField(max_length=10, default="Руб", verbose_name='Валюта')

    def __str__(self):
        return f"Payment #{self.id} ({self.status})"

    class Meta:
        verbose_name_plural = 'Оплаты'
        verbose_name = 'Оплата'