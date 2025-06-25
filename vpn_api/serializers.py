### serializers.py
from rest_framework import serializers
from .models import VPNServer, Subscription, SubscriptionPlan
from decimal import Decimal

class SubscriptionPlanSerializer(serializers.ModelSerializer):
    vpn_type_display = serializers.SerializerMethodField()
    duration_display = serializers.SerializerMethodField()
    current_price = serializers.SerializerMethodField()
    display_price = serializers.SerializerMethodField()
    has_referral_discount = serializers.SerializerMethodField()

    class Meta:
        model = SubscriptionPlan
        fields = [
            'id',
            'vpn_type',
            'vpn_type_display',
            'duration',
            'duration_display',
            'price',
            'discount_active',
            'discount_percent',
            'discount_price',
            'current_price',
            'display_price',
            'has_referral_discount',
        ]

    def get_vpn_type_display(self, obj):
        return obj.get_vpn_type_display()

    def get_duration_display(self, obj):
        return obj.get_duration_display()

    def get_current_price(self, obj):
        user = self.context.get('user')
        # Берём базовую цену тарифа (без скидки тарифа)
        base_price = obj.price
        # Применяем скидку тарифа, если она есть
        if obj.discount_active and obj.discount_price:
            price = obj.discount_price
        else:
            price = base_price
        # Применяем скидку реферала
        if user and getattr(user, 'referred_by', None):
            price = price * Decimal('0.90')
        return str(round(price, 2))

    def get_display_price(self, obj):
        user = self.context.get('user')
        # Берём базовую цену тарифа (без скидки тарифа)
        base_price = obj.price
        # Применяем скидку тарифа, если она есть
        if obj.discount_active and obj.discount_price:
            price = obj.discount_price
        else:
            price = base_price
        # Применяем скидку реферала
        if user and getattr(user, 'referred_by', None):
            return f"~{price}$~ {round(price * Decimal('0.90'), 2)}$"
        return obj.get_display_price()

    def get_has_referral_discount(self, obj):
        user = self.context.get('user')
        return bool(user and getattr(user, 'referred_by', None))


class BuySubscriptionSerializer(serializers.Serializer):
    plan_id = serializers.IntegerField()

    def validate(self, attrs):
        user = self.context['user']
        try:
            plan = SubscriptionPlan.objects.get(id=attrs['plan_id'])
        except SubscriptionPlan.DoesNotExist:
            raise serializers.ValidationError("Тариф не найден.")

        # Берём базовую цену тарифа (без скидки тарифа)
        base_price = plan.price
        # Применяем скидку тарифа, если она есть
        if plan.discount_active and plan.discount_price:
            current_price = plan.discount_price
        else:
            current_price = base_price
        # Скидка 10% для пользователей с рефералом
        if getattr(user, 'referred_by', None):
            current_price = current_price * Decimal('0.90')
        if user.balance < current_price:
            raise serializers.ValidationError("Недостаточно средств.")

        attrs['plan'] = plan
        attrs['price'] = current_price  # можно пробросить в view, чтобы не пересчитывать

        return attrs


class СountriesSerializer(serializers.ModelSerializer):
    class Meta:
        model = VPNServer
        fields = [
            'country',
            'name',
        ]