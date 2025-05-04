from django.contrib import admin
from .models import ProxyLog

@admin.register(ProxyLog)
class ProxyLogAdmin(admin.ModelAdmin):
    list_display = ("timestamp", "remote_ip", "domain", "status", "bytes_sent")
    search_fields = ("raw_log", "domain", "remote_ip")
