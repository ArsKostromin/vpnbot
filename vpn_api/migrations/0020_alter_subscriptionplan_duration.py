# Generated by Django 5.2.1 on 2025-05-28 09:49

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('vpn_api', '0019_subscriptionplan_discount_percent'),
    ]

    operations = [
        migrations.AlterField(
            model_name='subscriptionplan',
            name='duration',
            field=models.CharField(choices=[('1m', '1 месяц'), ('3m', '3 месяца'), ('6m', '6 месяца'), ('1y', '1 год')], max_length=2, verbose_name='Длительность'),
        ),
    ]
