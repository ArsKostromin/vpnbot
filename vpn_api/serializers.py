### serializers.py
from rest_framework import serializers
from .models import VPNServer, Subscription, SubscriptionPlan

class SubscriptionPlanSerializer(serializers.ModelSerializer):
    vpn_type_display = serializers.SerializerMethodField()
    duration_display = serializers.SerializerMethodField()
    current_price = serializers.SerializerMethodField()
    display_price = serializers.SerializerMethodField()

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
        ]

    def get_vpn_type_display(self, obj):
        return obj.get_vpn_type_display()

    def get_duration_display(self, obj):
        return obj.get_duration_display()

    def get_current_price(self, obj):
        return str(obj.get_current_price())

    def get_display_price(self, obj):
        return obj.get_display_price()


class BuySubscriptionSerializer(serializers.Serializer):
    plan_id = serializers.IntegerField()

    def validate(self, attrs):
        user = self.context['user']
        try:
            plan = SubscriptionPlan.objects.get(id=attrs['plan_id'])
        except SubscriptionPlan.DoesNotExist:
            raise serializers.ValidationError("Тариф не найден.")

        current_price = plan.get_current_price()
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