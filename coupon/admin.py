from django.contrib import admin
from django import forms
from .models import Coupon

class CouponAdminForm(forms.ModelForm):
    class Meta:
        model = Coupon
        fields = '__all__'

    def clean(self):
        cleaned_data = super().clean()
        coupon_type = cleaned_data.get("type")

        if coupon_type == 'balance':
            if not cleaned_data.get("discount_amount"):
                raise forms.ValidationError("Укажите сумму пополнения для купона на баланс.")
            # Удаляем лишние значения
            cleaned_data["vpn_type"] = None
            cleaned_data["duration"] = None

        elif coupon_type == 'subscription':
            if not cleaned_data.get("vpn_type") or not cleaned_data.get("duration"):
                raise forms.ValidationError("Укажите тип VPN и срок для подарочной подписки.")
            # Удаляем лишние значения
            cleaned_data["discount_amount"] = None

        return cleaned_data


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    form = CouponAdminForm
    list_display = ('code', 'type', 'expiration_date', 'is_used', 'used_by', 'discount_amount', 'vpn_type', 'duration')
    list_filter = ('type', 'vpn_type', 'duration', 'is_used', 'expiration_date')
    search_fields = ('code', 'used_by__email', 'used_by__telegram_id')
    readonly_fields = ('is_used', 'used_by')

    fieldsets = (
        (None, {
            'fields': ('code', 'type', 'expiration_date')
        }),
        ('Настройки для баланса', {
            'fields': ('discount_amount',),
            'classes': ('collapse',),
        }),
        ('Настройки для подписки', {
            'fields': ('vpn_type', 'duration'),
            'classes': ('collapse',),
        }),
        ('Служебные поля', {
            'fields': ('is_used', 'used_by'),
        }),
    )
