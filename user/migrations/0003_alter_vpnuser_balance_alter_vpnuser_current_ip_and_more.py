# Generated by Django 5.2 on 2025-04-30 08:35

import user.models
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0002_alter_vpnuser_options'),
    ]

    operations = [
        migrations.AlterField(
            model_name='vpnuser',
            name='balance',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10, verbose_name='Баланс'),
        ),
        migrations.AlterField(
            model_name='vpnuser',
            name='current_ip',
            field=models.GenericIPAddressField(blank=True, null=True, verbose_name='Ip'),
        ),
        migrations.AlterField(
            model_name='vpnuser',
            name='date_joined',
            field=models.DateTimeField(auto_now_add=True, verbose_name='Дата создания пользователя'),
        ),
        migrations.AlterField(
            model_name='vpnuser',
            name='is_active',
            field=models.BooleanField(default=True, verbose_name='Активен'),
        ),
        migrations.AlterField(
            model_name='vpnuser',
            name='is_banned',
            field=models.BooleanField(default=False, verbose_name='Забанен'),
        ),
        migrations.AlterField(
            model_name='vpnuser',
            name='is_staff',
            field=models.BooleanField(default=False, verbose_name='Админ'),
        ),
        migrations.AlterField(
            model_name='vpnuser',
            name='link_code',
            field=models.CharField(default=user.models.generate_link_code, max_length=12, unique=True, verbose_name='Для связи с приложением'),
        ),
        migrations.AlterField(
            model_name='vpnuser',
            name='telegram_id',
            field=models.BigIntegerField(blank=True, null=True, unique=True, verbose_name='Телеграм Id'),
        ),
    ]
