import logging
from django.contrib import admin
from django.utils.html import format_html_join
from django.urls import reverse
from django.utils.safestring import mark_safe
from django import forms
from django.utils import timezone
from django.contrib import messages

from .models import VPNUser
from proxy_logs.models import ProxyLog
from django.contrib.auth.models import Permission, Group
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.admin import GroupAdmin


logger = logging.getLogger(__name__)


class ProxyLogInline(admin.TabularInline):
    model = ProxyLog
    extra = 0
    fields = ("timestamp", "domain", "remote_ip")
    readonly_fields = ("timestamp", "domain", "remote_ip")
    can_delete = False
    show_change_link = True

    def get_formset(self, request, obj=None, **kwargs):
        formset = super().get_formset(request, obj, **kwargs)

        class LimitedFormSet(formset):
            def get_queryset(self, *args, **kwargs):
                qs = super().get_queryset(*args, **kwargs)
                return qs.order_by('-timestamp')[:80]  # ограничиваем тут безопасно

        return LimitedFormSet


class VPNUserAdminForm(forms.ModelForm):
    password = forms.CharField(
        label='Пароль',
        widget=forms.PasswordInput(),
        required=False,
        help_text='Оставьте пустым, чтобы не изменять пароль'
    )

    class Meta:
        model = VPNUser
        exclude = ['password']  # <-- убираем password из модели

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields['password'].help_text = 'Оставьте пустым, чтобы не изменять пароль'
        else:
            self.fields['password'].required = True
            self.fields['password'].help_text = 'Введите пароль для нового пользователя'

    def clean(self):
        cleaned_data = super().clean()
        if not self.instance.pk:
            email = cleaned_data.get('email')
            telegram_id = cleaned_data.get('telegram_id')
            if not email and not telegram_id:
                raise forms.ValidationError("Необходимо указать либо email, либо telegram_id")
        return cleaned_data

    def save(self, commit=True):
        # Получаем пользователя, но пока не сохраняем в базу
        user = super().save(commit=False)
        raw_password = self.cleaned_data.get('password')

        # Устанавливаем пароль, если он был введен в форме
        if raw_password:
            user.set_password(raw_password)
            logger.warning(
                f"Admin is changing password for user "
                f"Email: {user.email}, Telegram ID: {user.telegram_id}"
            )

        if commit:
            user.save()
        return user


@admin.register(VPNUser)
class VPNUserAdmin(admin.ModelAdmin):
    form = VPNUserAdminForm
    search_help_text = 'Поиск по email, Telegram ID или ID пользователя.'
    
    list_display = (
        'id', 'telegram_id', 'balance', 'is_banned', 'banned_at',
        'created_at', 'referrals_list', 'subscriptions_list'
    )
    list_filter = ('created_at', 'is_banned', 'banned_at')
    search_fields = ('email', 'telegram_id', 'id')
    actions = ['ban_users', 'unban_users']
    inlines = [ProxyLogInline]
    readonly_fields = ['view_logs_link', 'date_joined', 'uuid', 'last_login', 'banned_at']

    fieldsets = (
        (None, {'fields': ('email', 'telegram_id', 'password')}),
        (None, {'fields': ('balance', 'link_code', 'referred_by')}),
        ('Статус бана', {
            'fields': ('is_banned', 'ban_reason'),
            'classes': ('collapse',),
            'description': 'Управление статусом бана пользователя'
        }),
        ('Системная информация', {'fields': ('date_joined', 'uuid', 'last_login', 'banned_at')}),
        ('Разрешения', {'fields': ('is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Дополнительно', {'fields': ('view_logs_link',)}),
    )

    def ban_users(self, request, queryset):
        """Action для бана выбранных пользователей"""
        updated = queryset.update(
            is_banned=True,
            banned_at=timezone.now()
        )
        
        # Логируем действие
        for user in queryset:
            logger.warning(
                f"Admin {request.user} заблокировал пользователя "
                f"Email: {user.email}, Telegram ID: {user.telegram_id}"
            )
        
        self.message_user(
            request,
            f"Заблокировано {updated} пользователей.",
            messages.SUCCESS
        )
    ban_users.short_description = "Заблокировать выбранных пользователей"

    def unban_users(self, request, queryset):
        """Action для разбана выбранных пользователей"""
        updated = queryset.update(
            is_banned=False,
            banned_at=None
        )
        
        # Логируем действие
        for user in queryset:
            logger.warning(
                f"Admin {request.user} разблокировал пользователя "
                f"Email: {user.email}, Telegram ID: {user.telegram_id}"
            )
        
        self.message_user(
            request,
            f"Разблокировано {updated} пользователей.",
            messages.SUCCESS
        )
    unban_users.short_description = "Разблокировать выбранных пользователей"

    def save_model(self, request, obj, form, change):
        """
        Переопределяем сохранение. Теперь основная логика в form.save().
        """
        # Если это новый пользователь и пароль не задан, генерируем случайный.
        if not change and not form.cleaned_data.get('password'):
            import random
            import string
            password = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
            obj.set_password(password)
            self.message_user(request, f"Сгенерирован пароль для нового пользователя: {password}", level='INFO')

        # Сохраняем объект через form.save() или super()
        # form.save() вызовет наш переопределенный метод в VPNUserAdminForm
        super().save_model(request, obj, form, change)

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        """
        Фильтрует список прав пользователя, убирая все, что связано с Celery.
        """
        if db_field.name == "user_permissions":
            # Получаем Content Types, которые нужно исключить
            excluded_apps = ['django_celery_beat']
            excluded_cts = ContentType.objects.filter(app_label__in=excluded_apps)
            
            # Фильтруем права, исключая связанные с этими Content Types
            kwargs["queryset"] = Permission.objects.exclude(content_type__in=excluded_cts).select_related('content_type')
            
        return super().formfield_for_manytomany(db_field, request, **kwargs)

    def view_logs_link(self, obj):
        url = reverse("admin:proxy_logs_proxylog_changelist") + f"?user__id__exact={obj.id}"
        return mark_safe(f"<a href='{url}' target='_blank'>Посмотреть все логи</a>")
    view_logs_link.short_description = "Логи"

    def referrals_list(self, obj):
        referrals = obj.referrals.all()
        if not referrals:
            return "-"
        return format_html_join(
            '\n', "<div>{}</div>",
            ((f"{ref.telegram_id} / {ref.email or 'no email'}",) for ref in referrals)
        )
    referrals_list.short_description = "Рефералы"

    def subscriptions_list(self, obj):
        subscriptions = obj.subscriptions.select_related('plan').all()
        if not subscriptions:
            return "-"
        return format_html_join(
            '\n', "<div>{} — {} ({})</div>",
            (
                (
                    sub.plan.vpn_type if sub.plan else '–',
                    sub.start_date.strftime('%Y-%m-%d'),
                    "Активна" if sub.is_active else "Неактивна"
                ) for sub in subscriptions
            )
        )
    subscriptions_list.short_description = "Подписки"


# --- Кастомизация админки для Групп ---

class CustomGroupAdmin(GroupAdmin):
    """
    Кастомная админка для модели Group, чтобы отфильтровать права Celery.
    """
    def formfield_for_manytomany(self, db_field, request, **kwargs):
        if db_field.name == "permissions":
            excluded_apps = ['django_celery_beat']
            excluded_cts = ContentType.objects.filter(app_label__in=excluded_apps)
            kwargs["queryset"] = Permission.objects.exclude(content_type__in=excluded_cts).select_related('content_type')
        return super().formfield_for_manytomany(db_field, request, **kwargs)

# Отменяем регистрацию стандартной админки для Group
admin.site.unregister(Group)
# Регистрируем Group с нашей кастомной админкой
admin.site.register(Group, CustomGroupAdmin)
