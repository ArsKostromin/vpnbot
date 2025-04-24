from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.db import models
import uuid
import random
import string
from django.utils import timezone


def generate_link_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))


class VPNUserManager(BaseUserManager):
    def create_user(self, email=None, password=None, telegram_id=None, **extra_fields):
        if not email and not telegram_id:
            raise ValueError("Нужен либо email, либо telegram_id")

        if email:
            email = self.normalize_email(email)

        user = self.model(email=email, telegram_id=telegram_id, **extra_fields)

        if password:
            user.set_password(password)

        if not user.link_code:
            user.link_code = generate_link_code()

        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self.create_user(email=email, password=password, **extra_fields)


class VPNUser(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True, null=True, blank=True)
    telegram_id = models.BigIntegerField(unique=True, null=True, blank=True)
    link_code = models.CharField(max_length=12, unique=True, default=generate_link_code)

    # Вспомогательные поля
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    is_banned = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(auto_now_add=True)
    created_at = models.DateTimeField(default=timezone.now, verbose_name="Дата регистрации")
    current_ip = models.GenericIPAddressField(blank=True, null=True)
    
    objects = VPNUserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    def __str__(self):
        return self.email or f"Telegram User {self.telegram_id}"
