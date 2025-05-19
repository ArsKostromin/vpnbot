from django.contrib import admin
from django.utils.html import format_html, format_html_join
from .models import VPNUser
from proxy_logs.models import ProxyLog


class ProxyLogInline(admin.TabularInline):
    model = ProxyLog
    extra = 0
    fields = ("timestamp", "domain", "status", "bytes_sent", "remote_ip")
    readonly_fields = ("timestamp", "domain", "status", "bytes_sent", "remote_ip")
    can_delete = False
    show_change_link = True


@admin.register(VPNUser)
class VPNUserAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'telegram_id', 'balance', 'is_banned',
        'current_ip', 'created_at', 'referrals_list', 'subscriptions_list'  # ← добавлено
    )
    list_filter = ('is_banned', 'is_active', 'created_at')
    search_fields = ('email', 'telegram_id', 'current_ip', 'id')
    actions = ['ban_users', 'unban_users']
    inlines = [ProxyLogInline]
    
    def ban_users(self, request, queryset):
        queryset.update(is_banned=True)
    ban_users.short_description = "Забанить выбранных пользователей"

    def unban_users(self, request, queryset):
        queryset.update(is_banned=False)
    unban_users.short_description = "Разбанить выбранных пользователей"

    def referrals_list(self, obj):
        referrals = obj.referrals.all()
        if not referrals:
            return "-"
        return format_html_join(
            '\n', "<div>{}</div>", 
            ((f"{ref.telegram_id} / {ref.email or 'no email'}",) for ref in referrals)
        )
    referrals_list.short_description = "Рефералы"

    def subscriptions_list(self, obj):
        subscriptions = obj.subscriptions.select_related('plan').all()
        if not subscriptions:
            return "-"
        return format_html_join(
            '\n', "<div>{} — {} ({})</div>",
            (
                (
                    sub.plan.vpn_type if sub.plan else '–',
                    sub.start_date.strftime('%Y-%m-%d'),
                    "Активна" if sub.is_active else "Неактивна"
                ) for sub in subscriptions
            )
        )
    subscriptions_list.short_description = "Подписки"