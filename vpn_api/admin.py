from django.contrib import admin
from .models import SubscriptionPlan, Subscription

@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ('category_display', 'duration_display', 'price')
    list_filter = ('category', 'duration')
    search_fields = ('category',)

    def category_display(self, obj):
        return obj.get_category_display()
    category_display.short_description = "Категория"

    def duration_display(self, obj):
        return obj.get_duration_display()
    duration_display.short_description = "Длительность"

@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = (
        'user', 'plan', 'is_active', 'start_date', 'end_date', 
        'auto_renew', 'paused', 'short_vless_link'
    )
    list_filter = ('is_active', 'auto_renew', 'paused', 'plan__category')
    search_fields = (
        'user__email',
        'user__telegram_id',
        'plan__category',
        'plan__duration',
    )

    readonly_fields = ('vless',)

    def short_vless_link(self, obj):
        if obj.vless:
            return obj.vless[:40] + "..."
        return "-"
    short_vless_link.short_description = "VLESS"

# Отключаем лишнее из django-celery-beat
from django_celery_beat.models import (
    PeriodicTask, IntervalSchedule, CrontabSchedule,
    SolarSchedule, ClockedSchedule
)

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
