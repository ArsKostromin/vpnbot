from django.contrib import admin
from .models import VPNServer, Tariff, VPNKey, Subscription


@admin.register(VPNServer)
class VPNServerAdmin(admin.ModelAdmin):
    list_display = ('name', 'ip', 'port', 'protocol', 'country', 'is_active', 'limit_per_user')
    list_filter = ('protocol', 'country', 'is_active')
    search_fields = ('name', 'ip')


@admin.register(Tariff)
class TariffAdmin(admin.ModelAdmin):
    list_display = ('vpn_type', 'duration', 'price_usd')
    list_filter = ('vpn_type', 'duration')
    search_fields = ('vpn_type',)


@admin.register(VPNKey)
class VPNKeyAdmin(admin.ModelAdmin):
    list_display = ('key_short', 'vpn_user', 'server', 'is_active', 'created_at')
    list_filter = ('is_active', 'server')
    search_fields = ('key', 'vpn_user__telegram_id')

    def key_short(self, obj):
        return f"{obj.key[:6]}..."
    key_short.short_description = 'Ключ'


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ('vpn_user', 'tariff', 'vpn_key', 'start_date', 'end_date', 'is_active')
    list_filter = ('is_active', 'tariff__vpn_type', 'tariff__duration')
    search_fields = ('vpn_user__telegram_id',)
