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
    servers = VPNServer.objects.filter(is_active=True, country=country)
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

    if selected is None:
        # fallback
        try:
            fallback_server = VPNServer.objects.get(is_active=True, name="Indonesia")
            return fallback_server
        except VPNServer.DoesNotExist:
            return None

    return selected
