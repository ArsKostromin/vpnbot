# serializers.py
from rest_framework import serializers
from vpn_api.models import Subscription
from .models import VPNUser


class RegisterUserSerializer(serializers.Serializer):
    telegram_id = serializers.CharField(max_length=64)
    referral_code = serializers.CharField(max_length=32, required=False, allow_blank=True)

    def validate_telegram_id(self, value):
        if not value.isdigit():
            raise serializers.ValidationError("telegram_id должен содержать только цифры.")
        return value

    def validate_referral_code(self, value):
        if value and not value.isalnum():
            raise serializers.ValidationError("referral_code должен содержать только буквы и цифры.")
        return value


class SubscriptionSerializer(serializers.ModelSerializer):
    vpn_type = serializers.CharField(source='plan.vpn_type')
    duration = serializers.CharField(source='plan.duration')
    price = serializers.DecimalField(source='plan.price', max_digits=10, decimal_places=2)

    class Meta:
        model = Subscription
        fields = [
            'vpn_type',
            'duration',
            'price',
            'is_active',
            'start_date',
            'end_date',
            'auto_renew',
            'paused',
        ]


class UserInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = VPNUser
        fields = ('balance', 'link_code')
