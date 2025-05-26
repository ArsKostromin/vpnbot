# vpn_api/admin.py
from django.contrib import admin
from .models import SubscriptionPlan, Subscription


@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ('vpn_type', 'duration', 'price', 'discount_percent', 'discount_price', 'discount_active')
    list_filter = ('vpn_type', 'duration', 'discount_active')
    search_fields = ('vpn_type',)
    readonly_fields = ('discount_price',)

    def save_model(self, request, obj, form, change):
        if obj.discount_active and obj.discount_percent > 0:
            obj.discount_price = round(obj.price * (100 - obj.discount_percent) / 100, 2)
        else:
            obj.discount_price = None
        super().save_model(request, obj, form, change)

    def save_formset(self, request, form, formset, change):
        instances = formset.save(commit=False)
        for obj in instances:
            if isinstance(obj, SubscriptionPlan):
                if obj.discount_active and obj.discount_percent > 0:
                    obj.discount_price = round(obj.price * (100 - obj.discount_percent) / 100, 2)
                else:
                    obj.discount_price = None
            obj.save()
        formset.save_m2m()


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = (
        'user', 'plan', 'is_active', 'start_date', 'end_date',
        'auto_renew', 'paused', 'short_vless_link'
    )
    list_filter = ('is_active', 'auto_renew', 'paused')
    search_fields = (
        'user__email',
        'user__telegram_id',
        'plan__vpn_type',
        'plan__duration',
        'plan__price',
    )
    readonly_fields = ('vless',)

    def short_vless_link(self, obj):
        if obj.vless:
            return obj.vless[:40] + "..."
        return "-"
    short_vless_link.short_description = "VLESS"


# Отключение мусора от django-celery-beat
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
