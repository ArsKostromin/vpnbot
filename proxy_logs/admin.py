from django.contrib import admin
from django.contrib.auth import get_user_model
from django.utils.html import format_html
from django.urls import reverse
from .models import ProxyLog

User = get_user_model()

class ProxyLogInline(admin.TabularInline):
    model = ProxyLog
    extra = 0
    fields = ("timestamp", "remote_ip", "domain")
    readonly_fields = ("timestamp", "remote_ip", "domain")
    show_change_link = True

@admin.register(ProxyLog)
class ProxyLogAdmin(admin.ModelAdmin):
    list_display = ("timestamp", "linked_user", "remote_ip", "domain")
    search_fields = ("raw_log", "domain", "remote_ip", "user__email", "user__telegram_id")

    def linked_user(self, obj):
        if obj.user:
            url = reverse('admin:user_vpnuser_change', args=[obj.user.pk])
            return format_html('<a href="{}">{}</a>', url, str(obj.user))
        return "-"
    linked_user.short_description = "Пользователь"
    linked_user.admin_order_field = "user"

# # Админка кастомного пользователя с inlines
# class CustomUserAdmin(admin.ModelAdmin):
#     list_display = ("telegram_id", "email", "uuid", "is_active", "is_banned", "date_joined")
#     search_fields = ("email", "telegram_id", "uuid")
#     inlines = [ProxyLogInline]

# # Пере-регистрация модели пользователя
# admin.site.unregister(User)
# admin.site.register(User, CustomUserAdmin)
