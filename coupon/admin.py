from django.contrib import admin
from .models import Coupon


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = (
        'code',
        'type',
        'expiration_date',
        'is_used',
        'used_by_display',
        'vpn_usage',
        'duration',
        'discount_amount',
    )
    list_filter = ('type', 'vpn_usage', 'duration', 'is_used')
    search_fields = ('code', 'used_by__telegram_id', 'used_by__username')
    readonly_fields = ('code', 'used_by', 'is_used')

    def used_by_display(self, obj):
        if obj.used_by:
            return f"{obj.used_by.username or ''} ({obj.used_by.telegram_id})"
        return "-"
    used_by_display.short_description = 'Использовал'

    fieldsets = (
        (None, {
            'fields': ('code', 'type', 'expiration_date', 'is_used', 'used_by')
        }),
        ('Детали баланса', {
            'fields': ('discount_amount',),
            'classes': ('collapse',)
        }),
        ('Детали подписки', {
            'fields': ('vpn_usage', 'duration'),
            'classes': ('collapse',)
        }),
    )
