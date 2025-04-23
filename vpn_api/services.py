from datetime import timedelta
from django.db import transaction
from django.utils import timezone

from vpn_api.models import Tariff, Subscription, VPNKey, VPNServer
from user.models import VPNUser


@transaction.atomic
def create_subscription(user: VPNUser, vpn_type: str, duration: str) -> Subscription:
    tariff = Tariff.objects.get(vpn_type=vpn_type, duration=duration)

    if user.balance < tariff.price_usd:
        raise ValueError("Недостаточно средств на балансе")

    user.balance -= tariff.price_usd
    user.save()

    server = VPNServer.objects.filter(is_active=True).first()
    if not server:
        raise ValueError("Нет доступных VPN-серверов")

    key = VPNKey.objects.create(
        VPNUser=user,
        server=server,
        key=f"{user.telegram_id}-{timezone.now().timestamp()}",
    )

    months = int(duration.replace('m', ''))
    end_date = timezone.now() + timedelta(days=30 * months)

    subscription = Subscription.objects.create(
        VPNUser=user,
        tariff=tariff,
        vpn_key=key,
        end_date=end_date,
    )

    return subscription
