from django.contrib import admin
from django.utils.html import format_html_join
from django.urls import reverse
from django.utils.safestring import mark_safe

from .models import VPNUser
from proxy_logs.models import ProxyLog


class ProxyLogInline(admin.TabularInline):
    model = ProxyLog
    extra = 0
    fields = ("timestamp", "domain", "remote_ip")
    readonly_fields = ("timestamp", "domain", "remote_ip")
    can_delete = False
    show_change_link = True

    def get_formset(self, request, obj=None, **kwargs):
        formset = super().get_formset(request, obj, **kwargs)

        class LimitedFormSet(formset):
            def get_queryset(self, *args, **kwargs):
                qs = super().get_queryset(*args, **kwargs)
                return qs.order_by('-timestamp')[:80]  # ограничиваем тут безопасно

        return LimitedFormSet


@admin.register(VPNUser)
class VPNUserAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'telegram_id', 'balance',
        'created_at', 'referrals_list', 'subscriptions_list'
    )
    list_filter = ('created_at',)
    search_fields = ('email', 'telegram_id', 'current_ip', 'id')
    actions = []
    inlines = [ProxyLogInline]
    readonly_fields = ['view_logs_link']
    exclude = ['is_banned', 'is_active']

    def view_logs_link(self, obj):
        url = reverse("admin:proxy_logs_proxylog_changelist") + f"?user__id__exact={obj.id}"
        return mark_safe(f"<a href='{url}' target='_blank'>Посмотреть все логи</a>")
    view_logs_link.short_description = "Логи"

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
