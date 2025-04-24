from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import VPNUser

@admin.register(VPNUser)
class VPNUserAdmin(BaseUserAdmin):
    model = VPNUser
    list_display = (
        'email', 'telegram_id', 'balance', 'is_banned', 'is_staff', 'created_at', 'current_ip'
    )
    list_filter = ('is_banned', 'is_staff', 'is_active')
    search_fields = ('email', 'telegram_id', 'link_code')
    ordering = ('-created_at',)

    fieldsets = (
        (None, {'fields': ('email', 'telegram_id', 'password')}),
        ('Личная информация', {'fields': ('balance', 'link_code', 'current_ip')}),
        ('Права доступа', {'fields': ('is_active', 'is_staff', 'is_superuser', 'is_banned', 'groups', 'user_permissions')}),
        ('Даты', {'fields': ('date_joined', 'created_at')}),
    )

    readonly_fields = ('created_at', 'date_joined')

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'telegram_id', 'password1', 'password2', 'is_staff', 'is_superuser'),
        }),
    )
