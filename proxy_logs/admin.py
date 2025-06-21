from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.urls import reverse
from .models import ProxyLog


@admin.register(ProxyLog)
class ProxyLogAdmin(admin.ModelAdmin):
    search_help_text = 'Поиск по IP-адресу, домену, email или Telegram ID пользователя.'
    list_display = ("remote_ip", "linked_user", "timestamp")
    search_fields = ("raw_log", "domain", "remote_ip", "user__email", "user__telegram_id")
    fields = ("remote_ip", "linked_user", "domain", "timestamp", "user_logs")
    readonly_fields = ("user_logs", "timestamp", "linked_user")

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
        logs = ProxyLog.objects.filter(user=obj.user).exclude(pk=obj.pk).order_by("-timestamp")[:20]
        if not logs:
            return "—"
        html = """
        <style>
            table.user-logs-table th, table.user-logs-table td {
                padding: 4px 8px;
                border: 1px solid #ccc;
            }
        </style>
        <table class="user-logs-table">
            <thead>
                <tr>
                    <th>Время</th>
                    <th>IP</th>
                    <th>Домен</th>
                    <th>Открыть</th>
                </tr>
            </thead>
            <tbody>
        """
        for log in logs:
            log_url = reverse("admin:proxy_logs_proxylog_change", args=[log.pk])
            html += f"""
                <tr>
                    <td>{log.timestamp.strftime('%Y-%m-%d %H:%M:%S')}</td>
                    <td>{log.remote_ip}</td>
                    <td>{log.domain}</td>
                    <td><a href="{log_url}">Открыть</a></td>
                </tr>
            """
        html += "</tbody></table>"
        return mark_safe(html)

    user_logs.short_description = "Другие логи этого пользователя"
