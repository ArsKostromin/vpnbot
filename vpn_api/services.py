# services.py

from .utils import get_duration_delta
from .models import VPNServer

def extend_subscription(subscription, plan):
    delta = get_duration_delta(plan.duration)
    if not delta:
        raise ValueError("Неизвестная длительность плана")

    subscription.end_date += delta
    subscription.save()
    return subscription

def get_least_loaded_server():
    servers = VPNServer.objects.filter(is_active=True)
    min_count = float('inf')
    selected = None

    for server in servers:
        try:
            r = requests.get(f"{server.api_url}/stats", timeout=5)
            count = r.json().get("user_count", 9999)
            if count < min_count:
                selected, min_count = server, count
        except:
            continue

    return selected


def get_least_loaded_server_by_country(country: str):
    # Сначала пытаемся найти по стране
    server = VPNServer.objects.filter(is_active=True, country=country).first()
    
    if server:
        return server

    # Если не нашли — берём любой активный
    return VPNServer.objects.filter(is_active=True).first()
