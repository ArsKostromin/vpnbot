### serializers.py
from rest_framework import serializers
from .models import VPNServer, Subscription, SubscriptionPlan
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)

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
        logger.warning(f"get_current_price: user={user}, plan_id={obj.id}, plan_price={obj.price}")
        
        base_price = obj.price
        if obj.discount_active and obj.discount_price:
            price = obj.discount_price
            logger.warning(f"Применена скидка тарифа: {base_price} -> {price}")
        else:
            price = base_price
            logger.warning(f"Скидка тарифа не применяется: {price}")
        
        # Скидка только если у пользователя есть хотя бы один реферал
        if user and hasattr(user, 'referrals') and user.referrals.exists():
            old_price = price
            price = price * Decimal('0.90')
            logger.warning(f"Применена скидка реферала: {old_price} -> {price} (user.referrals_count={user.referrals.count()})")
        else:
            logger.warning(f"Скидка реферала не применяется: user={user}, referrals_count={user.referrals.count() if user else None}")
        
        result = str(round(price, 2))
        logger.warning(f"Итоговая цена: {result}")
        return result

    def get_display_price(self, obj):
        user = self.context.get('user')
        logger.warning(f"get_display_price: user={user}, plan_id={obj.id}")
        
        base_price = obj.price
        if obj.discount_active and obj.discount_price:
            price = obj.discount_price
        else:
            price = base_price
        
        if user and hasattr(user, 'referrals') and user.referrals.exists():
            result = f"~{price}$~ {round(price * Decimal('0.90'), 2)}$"
            logger.warning(f"Отображение скидки реферала: {result}")
            return result
        else:
            result = obj.get_display_price()
            logger.warning(f"Обычное отображение цены: {result}")
            return result

    def get_has_referral_discount(self, obj):
        user = self.context.get('user')
        has_discount = bool(user and hasattr(user, 'referrals') and user.referrals.exists())
        logger.warning(f"has_referral_discount: user={user}, has_discount={has_discount}, referrals_count={user.referrals.count() if user else None}")
        return has_discount


class BuySubscriptionSerializer(serializers.Serializer):
    plan_id = serializers.IntegerField()

    def validate(self, attrs):
        user = self.context['user']
        try:
            plan = SubscriptionPlan.objects.get(id=attrs['plan_id'])
        except SubscriptionPlan.DoesNotExist:
            raise serializers.ValidationError("Тариф не найден.")

        base_price = plan.price
        if plan.discount_active and plan.discount_price:
            current_price = plan.discount_price
        else:
            current_price = base_price
        # Скидка только если у пользователя есть хотя бы один реферал
        if hasattr(user, 'referrals') and user.referrals.exists():
            current_price = current_price * Decimal('0.90')
        if user.balance < current_price:
            raise serializers.ValidationError("Недостаточно средств.")

        attrs['plan'] = plan
        attrs['price'] = current_price

        return attrs


class СountriesSerializer(serializers.ModelSerializer):
    class Meta:
        model = VPNServer
        fields = [
            'country',
            'name',
        ]