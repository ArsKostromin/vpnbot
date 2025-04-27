from rest_framework import serializers
from vpn_api.models import Subscription
from .models import VPNUser

# serializers/subscription.py

class SubscriptionSerializer(serializers.ModelSerializer):
    # Берём поле 'vpn_type' из связанной модели SubscriptionPlan через ForeignKey 'plan'
    vpn_type = serializers.CharField(source='plan.vpn_type')
    duration = serializers.CharField(source='plan.duration')
    # И цену тоже достаём из связанной модели; обязательно указываем max_digits и decimal_places
    price = serializers.DecimalField(source='plan.price', max_digits=10, decimal_places=2)

    class Meta:
        model = Subscription  # Модель, которую сериализуем
        fields = [
            'vpn_type',     # Тип VPN (например, solo/double/triple)
            'duration',     # Длительность подписки (1m/6m/1y/3y)
            'price',        # Цена подписки
            'is_active',    # Активна ли подписка сейчас
            'start_date',   # Дата начала подписки
            'end_date',     # Дата окончания подписки
            'auto_renew',   # Включено ли авто-продление
            'paused',       # Приостановлена ли подписка
        ]


class UserInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = VPNUser
        fields = ('balance', 'link_code')