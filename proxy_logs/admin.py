from django.contrib import admin
from .models import ProxyLog

@admin.register(ProxyLog)
class ProxyLogAdmin(admin.ModelAdmin):
    list_display = ("user", "timestamp", "remote_ip", "domain")
    search_fields = ("raw_log", "domain", "remote_ip", "user__email", "user__telegram_id")
