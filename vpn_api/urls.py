from django.contrib import admin
from django.urls import path, include
from django.urls import re_path
from .views import TelegramWebhookView


urlpatterns = [
    path("bot/webhook/", TelegramWebhookView.as_view())
]