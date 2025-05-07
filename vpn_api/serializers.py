### serializers.py
from rest_framework import serializers
from .models import Subscription, SubscriptionPlan

class SubscriptionPlanSerializer(serializers.ModelSerializer):
    vpn_type_display = serializers.CharField(source='get_vpn_type_display', read_only=True)
    duration_display = serializers.CharField(source='get_duration_display', read_only=True)

    class Meta:
        model = SubscriptionPlan
        fields = [
            'id', 'vpn_type', 'vpn_type_display', 
            'duration', 'duration_display', 'price'
        ]


class BuySubscriptionSerializer(serializers.Serializer):
    plan_id = serializers.IntegerField()

    def validate(self, attrs):
        user = self.context['user']
        try:
            plan = SubscriptionPlan.objects.get(id=attrs['plan_id'])
        except SubscriptionPlan.DoesNotExist:
            raise serializers.ValidationError("Тариф не найден.")

        if user.balance < plan.price:
            raise serializers.ValidationError("Недостаточно средств.")

        attrs['plan'] = plan
        return attrs
