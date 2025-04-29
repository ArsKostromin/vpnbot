# from django.contrib import admin
# from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
# from .models import VPNUser

# @admin.register(VPNUser)
# class VPNUserAdmin(BaseUserAdmin):
#     model = VPNUser
#     list_display = (
#         'email', 'telegram_id', 'balance', 'is_banned', 'is_staff', 'created_at', 'current_ip'
#     )
#     list_filter = ('is_banned', 'is_staff', 'is_active')
#     search_fields = ('email', 'telegram_id', 'link_code')
#     ordering = ('-created_at',)

#     fieldsets = (
#         (None, {'fields': ('email', 'telegram_id', 'password')}),
#         ('Личная информация', {'fields': ('balance', 'link_code', 'current_ip')}),
#         ('Права доступа', {'fields': ('is_active', 'is_staff', 'is_superuser', 'is_banned', 'groups', 'user_permissions')}),
#         ('Даты', {'fields': ('date_joined', 'created_at')}),
#     )

#     readonly_fields = ('created_at', 'date_joined')

#     add_fieldsets = (
#         (None, {
#             'classes': ('wide',),
#             'fields': ('email', 'telegram_id', 'password1', 'password2', 'is_staff', 'is_superuser'),
#         }),
#     )

# user/admin.py
from django.contrib import admin
from django.utils.html import format_html
from .models import VPNUser

@admin.register(VPNUser)
class VPNUserAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'email', 'telegram_id', 'balance', 'is_banned', 'is_active',
        'current_ip', 'created_at'
    )
    list_filter = ('is_banned', 'is_active', 'created_at')
    search_fields = ('email', 'telegram_id', 'current_ip', 'id')
    actions = ['ban_users', 'unban_users']

    def ban_users(self, request, queryset):
        queryset.update(is_banned=True)
    ban_users.short_description = "Забанить выбранных пользователей"

    def unban_users(self, request, queryset):
        queryset.update(is_banned=False)
    unban_users.short_description = "Разбанить выбранных пользователей"