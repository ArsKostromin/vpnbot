from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.db import models
import uuid
import random
import string
from django.utils import timezone

# Функция для генерации случайного кода приглашения (из букв и цифр)
def generate_link_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))


# Кастомный менеджер пользователей
class VPNUserManager(BaseUserManager):
    def create_user(self, email=None, password=None, telegram_id=None, **extra_fields):
        # Требуется либо email, либо telegram_id
        if not email and not telegram_id:
            raise ValueError("Нужен либо email, либо telegram_id")

        if email:
            email = self.normalize_email(email)

        # Создание экземпляра пользователя
        user = self.model(email=email, telegram_id=telegram_id, **extra_fields)

        # Установка пароля (если передан)
        if password:
            user.set_password(password)

        # Генерация кода приглашения, если не задан
        if not user.link_code:
            user.link_code = generate_link_code()

        # Сохраняем пользователя в базу
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        # Создание суперпользователя с флагами is_staff и is_superuser
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self.create_user(email=email, password=password, **extra_fields)


# Модель пользователя VPN
class VPNUser(AbstractBaseUser, PermissionsMixin):
    # Основные поля
    email = models.EmailField(unique=True, null=True, blank=True)  # Email (уникальный, может быть пустым)
    telegram_id = models.BigIntegerField(unique=True, null=True, blank=True, verbose_name='Телеграм Id')  # Telegram ID пользователя
    link_code = models.CharField(max_length=12, unique=True, default=generate_link_code, verbose_name='Для связи с приложением')  # Уникальный код приглашения

    # Вспомогательные поля
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='Баланс')  # Баланс пользователя в рублях
    is_staff = models.BooleanField(default=False, verbose_name='Админ')  # Может ли пользователь зайти в админку
    date_joined = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания пользователя')  # Дата создания пользователя
    created_at = models.DateTimeField(default=timezone.now, verbose_name="Дата регистрации")  # Альтернативное поле даты
    referred_by = models.ForeignKey("self", null=True, blank=True, on_delete=models.SET_NULL, related_name="referrals", verbose_name="Пригласивший")
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, verbose_name="UUID")

    # --- Поля для механики бана ---
    is_banned = models.BooleanField(default=False, verbose_name="Забанен")
    ban_reason = models.TextField(blank=True, null=True, verbose_name="Причина бана")
    banned_at = models.DateTimeField(null=True, blank=True, verbose_name="Дата бана")
    
    # Указываем кастомный менеджер
    objects = VPNUserManager()

    # Уникальный идентификатор пользователя (для логина)
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []  # При создании суперпользователя дополнительных обязательных полей нет

    def __str__(self):
        # Представление объекта в виде строки
        return self.email or f"Telegram User {self.telegram_id}"

    class Meta:
        verbose_name_plural = 'Пользователи'
        verbose_name = 'Пользователь'
    
    def save(self, *args, **kwargs):
        # Автоматически устанавливаем дату бана при первом бане
        if self.is_banned and not self.banned_at:
            self.banned_at = timezone.now()
        # Сбрасываем дату бана при разбане
        elif not self.is_banned and self.banned_at:
            self.banned_at = None
            
        super().save(*args, **kwargs)
        
    def apply_coupon(self, coupon_code: str):
        try:
            coupon = Coupon.objects.get(code=coupon_code)

            if coupon.is_used:
                return "Этот промокод уже использован."
            if coupon.expiration_date < timezone.now():
                return "Срок действия промокода истёк."

            if coupon.type == 'balance':
                if coupon.discount_amount is None:
                    return "Некорректный промокод."
                self.balance += coupon.discount_amount
                self.save()

            elif coupon.type == 'subscription':
                if not coupon.vpn_type or not coupon.duration:
                    return "Некорректный промокод."

                # Найдём план, соответствующий параметрам промокода
                try:
                    plan = SubscriptionPlan.objects.get(
                        vpn_type=coupon.vpn_type,
                        duration=coupon.duration
                    )
                except SubscriptionPlan.DoesNotExist:
                    return "Не найден подходящий тарифный план."

                # Создаём подписку
                subscription = Subscription.objects.create(
                    user=self,
                    plan=plan,
                    auto_renew=False,  # подарочные — без автопродления
                    is_active=True,
                )
                subscription.save()

            coupon.is_used = True
            coupon.used_by = self
            coupon.save()

            return "Промокод успешно применён!"

        except Coupon.DoesNotExist:
            return "Промокод не найден."
