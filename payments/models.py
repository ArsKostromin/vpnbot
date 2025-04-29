from django.db import models
from user.models import VPNUser

class Payment(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', 'В ожидании'
        SUCCESS = 'success', 'Успешно'
        FAIL = 'fail', 'Ошибка'

    user = models.ForeignKey(VPNUser, on_delete=models.CASCADE, related_name='payments')
    inv_id = models.PositiveIntegerField(unique=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Payment #{self.inv_id} ({self.status})"

    class Meta:
        verbose_name_plural = 'Оплаты'
        verbose_name = 'Оплата'