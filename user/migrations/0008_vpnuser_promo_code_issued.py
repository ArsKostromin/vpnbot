# Generated by Django 5.2.3 on 2025-06-23 17:47

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0007_vpnuser_ban_reason_vpnuser_banned_at_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='vpnuser',
            name='promo_code_issued',
            field=models.BooleanField(default=False, verbose_name='Промокод выдан'),
        ),
    ]
