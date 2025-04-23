from rest_framework import serializers
from vpn_api.models import Tariff, Subscription
from user.models import VPNUser
from vpn_api.services import create_subscription


class SelectTypeSerializer(serializers.Serializer):
    vpn_type = serializers.ChoiceField(choices=[('mobile', 'Мобильный'), ('residential', 'Резидентский'), ('rotating', 'Ротация')])


class SelectDurationSerializer(serializers.Serializer):
    vpn_type = serializers.CharField()
    duration = serializers.ChoiceField(choices=[('1m', '1 месяц'), ('6m', '6 месяцев'), ('12m', '1 год'), ('36m', '3 года')])


class PurchaseSubscriptionSerializer(serializers.Serializer):
    vpn_type = serializers.CharField()
    duration = serializers.CharField()

    def validate(self, data):
        user = self.context['request'].user
        try:
            tariff = Tariff.objects.get(vpn_type=data['vpn_type'], duration=data['duration'])
        except Tariff.DoesNotExist:
            raise serializers.ValidationError("Такой тариф не существует")

        if user.balance < tariff.price_usd:
            raise serializers.ValidationError("Недостаточно средств на балансе")

        return data

    def create(self, validated_data):
        user = self.context['request'].user
        return create_subscription(user, validated_data['vpn_type'], validated_data['duration'])
