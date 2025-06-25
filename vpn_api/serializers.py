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
        logger.info(f"get_current_price: user={user}, plan_id={obj.id}, plan_price={obj.price}")
        
        # Берём базовую цену тарифа (без скидки тарифа)
        base_price = obj.price
        # Применяем скидку тарифа, если она есть
        if obj.discount_active and obj.discount_price:
            price = obj.discount_price
            logger.info(f"Применена скидка тарифа: {base_price} -> {price}")
        else:
            price = base_price
            logger.info(f"Скидка тарифа не применяется: {price}")
        
        # Применяем скидку реферала
        if user and getattr(user, 'referred_by', None):
            old_price = price
            price = price * Decimal('0.90')
            logger.info(f"Применена скидка реферала: {old_price} -> {price} (user.referred_by={user.referred_by})")
        else:
            logger.info(f"Скидка реферала не применяется: user={user}, referred_by={getattr(user, 'referred_by', None) if user else None}")
        
        result = str(round(price, 2))
        logger.info(f"Итоговая цена: {result}")
        return result

    def get_display_price(self, obj):
        user = self.context.get('user')
        logger.info(f"get_display_price: user={user}, plan_id={obj.id}")
        
        # Берём базовую цену тарифа (без скидки тарифа)
        base_price = obj.price
        # Применяем скидку тарифа, если она есть
        if obj.discount_active and obj.discount_price:
            price = obj.discount_price
        else:
            price = base_price
        
        # Применяем скидку реферала
        if user and getattr(user, 'referred_by', None):
            result = f"~{price}$~ {round(price * Decimal('0.90'), 2)}$"
            logger.info(f"Отображение скидки реферала: {result}")
            return result
        else:
            result = obj.get_display_price()
            logger.info(f"Обычное отображение цены: {result}")
            return result

    def get_has_referral_discount(self, obj):
        user = self.context.get('user')
        has_discount = bool(user and getattr(user, 'referred_by', None))
        logger.info(f"has_referral_discount: user={user}, has_discount={has_discount}, referred_by={getattr(user, 'referred_by', None) if user else None}")
        return has_discount


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