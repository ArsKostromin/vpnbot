# Generated by Django 5.2 on 2025-05-04 14:31

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('proxy_logs', '0001_initial'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='proxylog',
            name='user',
        ),
        migrations.AlterField(
            model_name='proxylog',
            name='remote_ip',
            field=models.GenericIPAddressField(blank=True, null=True, verbose_name='IP-адрес клиента'),
        ),
        migrations.AlterField(
            model_name='proxylog',
            name='timestamp',
            field=models.DateTimeField(auto_now_add=True, verbose_name='Дата и время записи'),
        ),
    ]
