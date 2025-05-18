from django.contrib import admin
from .models import ProxyLog

@admin.register(ProxyLog)
class ProxyLogAdmin(admin.ModelAdmin):
    list_display = ("user", "timestamp", "remote_ip", "domain", "status", "bytes_sent")
    search_fields = ("user", "raw_log", "domain", "remote_ip")
