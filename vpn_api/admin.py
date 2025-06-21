# vpn_api/admin.py
from django.contrib import admin
from .models import SubscriptionPlan, Subscription, VPNServer

@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    search_help_text = 'Поиск по типу VPN.'
    list_display = ('vpn_type', 'duration', 'price', 'discount_percent', 'discount_price', 'discount_active')
    list_filter = ('vpn_type', 'duration', 'discount_active')
    search_fields = ('vpn_type',)
    readonly_fields = ('discount_price',)
    
@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    search_help_text = 'Поиск по email, Telegram ID, UUID, типу, длительности или цене тарифа.'
    list_display = (
        'user', 'plan', 'is_active', 'start_date', 'end_date',
        'auto_renew', 'short_vless_link', 'uuid'  # <-- показываем UUID в списке
    )
    list_filter = ('is_active', 'auto_renew')
    search_fields = (
        'user__email',
        'user__telegram_id',
        'plan__vpn_type',
        'plan__duration',
        'plan__price',
        'uuid',  # <-- поиск по UUID
    )
    readonly_fields = ('vless', 'is_active', 'server')  # <-- UUID убираем отсюда


    def short_vless_link(self, obj):
        if obj.vless:
            return obj.vless[:40] + "..."
        return "-"
    short_vless_link.short_description = "VLESS"

@admin.register(VPNServer)
class VPNServerAdmin(admin.ModelAdmin):
    search_help_text = 'Поиск по названию, стране, домену или URL.'
    list_display = ('name', 'country', 'domain', 'api_url', 'is_active')
    list_filter = ('is_active', 'country')
    search_fields = ('name', 'country', 'domain', 'api_url')

# --- Безопасное удаление моделей из админки ---
from django_celery_beat.models import (
    PeriodicTask, IntervalSchedule, CrontabSchedule,
    SolarSchedule, ClockedSchedule
)

def safe_unregister(model):
    """Безопасно отменяет регистрацию модели, игнорируя ошибку, если модель не была зарегистрирована."""
    try:
        admin.site.unregister(model)
    except admin.sites.NotRegistered:
        pass

# Убираем стандартные модели Celery Beat из админки
safe_unregister(PeriodicTask)
safe_unregister(IntervalSchedule)
safe_unregister(CrontabSchedule)
safe_unregister(SolarSchedule)
safe_unregister(ClockedSchedule)