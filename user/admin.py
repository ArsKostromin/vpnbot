from django.contrib import admin
from .models import VPNUser

@admin.register(VPNUser)
class VPNUserAdmin(admin.ModelAdmin):
    list_display = ('telegram_id', 'vpn_type', 'current_ip', 'created_at', 'vpn_key')  # Отображение в списке
    list_filter = ('vpn_type', 'created_at')  # Фильтры по бокам
    search_fields = ('telegram_id', 'vpn_key')  # Поиск
    readonly_fields = ('created_at', 'vpn_key')  # Только для чтения
    ordering = ('-created_at',)  # Сортировка по дате создания

    fieldsets = (
        (None, {
            'fields': ('telegram_id', 'vpn_type', 'current_ip')
        }),
        ('Технические данные', {
            'fields': ('vpn_key', 'created_at'),
            'classes': ('collapse',),  # Свернутый блок
        }),
    )
