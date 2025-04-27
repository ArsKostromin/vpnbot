import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')  # Путь до settings.py

app = Celery('vpnbot')

app.config_from_object('django.conf:settings', namespace='CELERY')

app.autodiscover_tasks()
