from django.contrib import admin
from .models import VPNUser


@admin.register(VPNUser)
class VPNUserAdmin(admin.ModelAdmin):
    list_display = (
        'telegram_id', 
        'username', 
        'created_at', 
        'current_ip',
        'balance',
        'is_banned',
    )
    list_filter = ('is_banned', 'created_at')
    search_fields = ('telegram_id', 'username')
    readonly_fields = ('telegram_id', 'created_at', 'referred_by')

    fieldsets = (
        (None, {
            'fields': ('telegram_id', 'username', 'current_ip')
        }),
        ('Доп. информация', {
            'fields': ('referred_by', 'balance', 'is_banned', 'created_at')
        }),
    )

    ordering = ('-created_at',)
