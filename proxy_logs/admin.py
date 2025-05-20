from django.contrib import admin
from django.contrib.auth import get_user_model
from django.utils.html import format_html
from django.urls import reverse
from .models import ProxyLog
from django.utils.safestring import mark_safe


@admin.register(ProxyLog)
class ProxyLogAdmin(admin.ModelAdmin):
    list_display = ("remote_ip", "linked_user", "timestamp", "domain")
    search_fields = ("raw_log", "domain", "remote_ip", "user__email", "user__telegram_id")
    readonly_fields = ("user_logs",)

    def linked_user(self, obj):
        if obj.user:
            url = reverse('admin:user_vpnuser_change', args=[obj.user.pk])
            return format_html('<a href="{}">{}</a>', url, str(obj.user))
        return "-"
    linked_user.short_description = "Пользователь"
    linked_user.admin_order_field = "user"

    def user_logs(self, obj):
        if not obj.user:
            return "—"
        logs = ProxyLog.objects.filter(user=obj.user).order_by("-timestamp")[:20]
        html = "<ul>"
        for log in logs:
            html += f"<li>{log.timestamp} — {log.remote_ip} — {log.domain}</li>"
        html += "</ul>"
        return mark_safe(html)

    user_logs.short_description = "Логи этого пользователя"