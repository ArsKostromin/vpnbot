# Generated by Django 5.2 on 2025-05-07 10:42

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('coupon', '0003_alter_coupon_vpn_type'),
    ]

    operations = [
        migrations.AlterField(
            model_name='coupon',
            name='duration',
            field=models.CharField(blank=True, choices=[('1m', '1 месяц'), ('6m', '6 месяцев'), ('1y', '1 год'), ('3y', '3 года')], max_length=3, null=True, verbose_name='Срок'),
        ),
    ]
