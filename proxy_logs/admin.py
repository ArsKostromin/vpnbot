from django.contrib import admin
from django.contrib.auth import get_user_model
from .models import ProxyLog

User = get_user_model()

class ProxyLogInline(admin.TabularInline):
    model = ProxyLog
    extra = 0
    fields = ("timestamp", "remote_ip", "domain", "status", "bytes_sent")
    readonly_fields = ("timestamp", "remote_ip", "domain", "status", "bytes_sent")
    show_change_link = True

@admin.register(ProxyLog)
class ProxyLogAdmin(admin.ModelAdmin):
    list_display = ("timestamp", "user", "remote_ip", "domain", "status", "bytes_sent")
    search_fields = ("raw_log", "domain", "remote_ip")

# Переопределим UserAdmin
class CustomUserAdmin(admin.ModelAdmin):
    inlines = [ProxyLogInline]

# Удаляем старую регистрацию User, если была, и регистрируем заново
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)
