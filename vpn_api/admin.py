# from django.contrib import admin
# from .models import Subscription, SubscriptionPlan

# @admin.register(SubscriptionPlan)
# class SubscriptionPlanAdmin(admin.ModelAdmin):
#     list_display = ('vpn_type', 'duration', 'price')
#     list_filter = ('vpn_type', 'duration')

# @admin.register(Subscription)
# class SubscriptionAdmin(admin.ModelAdmin):
#     list_display = ('user', 'plan', 'is_active', 'start_date', 'end_date')
#     list_filter = ('plan__vpn_type', 'plan__duration', 'is_active')


# vpn_api/admin.py
from django.contrib import admin
from .models import SubscriptionPlan, Subscription

@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ('vpn_type', 'duration', 'price')
    list_filter = ('vpn_type', 'duration')
    search_fields = ('vpn_type',)

@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ('user', 'plan', 'is_active', 'start_date', 'end_date', 'auto_renew', 'paused')
    list_filter = ('is_active', 'auto_renew', 'paused')
    search_fields = ('user__email', 'user__telegram_id')