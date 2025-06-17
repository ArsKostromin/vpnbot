# vpn_api/admin.py
from django.contrib import admin
from .models import SubscriptionPlan, Subscription, VPNServer
from django_celery_beat.models import (
    PeriodicTask, IntervalSchedule, CrontabSchedule,
    SolarSchedule, ClockedSchedule
)


@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ('vpn_type', 'duration', 'price', 'discount_percent', 'discount_price', 'discount_active')
    list_filter = ('vpn_type', 'duration', 'discount_active')
    search_fields = ('vpn_type',)
    readonly_fields = ('discount_price',)
    exclude = ('discount_text',)


# @admin.action(description="Сгенерировать VLESS для выбранных подписок")
# def generate_vless_action(modeladmin, request, queryset):
#     for sub in queryset:
#         if not sub.vless:
#             try:
#                 server = get_least_loaded_server()
#                 vless_result = create_vless(server, user_uuid)
#                 sub добавить vless_result
#                 sub.save()
#             except Exception as e:
#                 modeladmin.message_user(request, f"Ошибка для {sub.id}: {str(e)}", level='error')


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = (
        'user', 'plan', 'is_active', 'start_date', 'end_date',
        'auto_renew', 'paused', 'short_vless_link', 'uuid'
    )
    list_filter = ('is_active', 'auto_renew', 'paused')
    search_fields = (
        'user__email',
        'user__telegram_id',
        'plan__vpn_type',
        'plan__duration',
        'plan__price',
        'uuid',
    )
    readonly_fields = ('vless',)
    actions = [generate_vless_action]

    def short_vless_link(self, obj):
        if obj.vless:
            return obj.vless[:40] + "..."
        return "-"
    short_vless_link.short_description = "VLESS"


@admin.register(VPNServer)
class VPNServerAdmin(admin.ModelAdmin):
    list_display = ('name', 'country', 'domain', 'api_url', 'is_active')
    list_filter = ('is_active', 'country')
    search_fields = ('name', 'country', 'domain', 'api_url')


def safe_unregister(model):
    try:
        admin.site.unregister(model)
    except admin.sites.NotRegistered:
        pass

safe_unregister(PeriodicTask)
safe_unregister(IntervalSchedule)
safe_unregister(CrontabSchedule)
safe_unregister(SolarSchedule)
safe_unregister(ClockedSchedule)
