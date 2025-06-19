# services.py

from .utils import get_duration_delta
from .models import VPNServer
from urllib.parse import urljoin
import logging
import requests

def extend_subscription(subscription, plan):
    delta = get_duration_delta(plan.duration)
    if not delta:
        raise ValueError("Неизвестная длительность плана")

    subscription.end_date += delta
    subscription.save()
    return subscription

logger = logging.getLogger(__name__)

def get_least_loaded_server():
    servers = VPNServer.objects.filter(is_active=True)

    if not servers.exists():
        logger.warning("Нет активных серверов в базе")
        return None

    min_count = float('inf')
    selected = None

    for server in servers:
        try:
            # Убедимся, что URL заканчивается без слеша, а путь — с ним
            endpoint = urljoin(server.api_url.rstrip('/') + '/', 'vless/count')
            logger.debug(f"Запрос к серверу {server.name}: {endpoint}")
            
            response = requests.get(endpoint, timeout=5)
            response.raise_for_status()
            data = response.json()

            count = int(data.get("user_count", 9999))
            logger.debug(f"{server.name} (user_count = {count})")

        except Exception as e:
            logger.warning(f"Ошибка при запросе к серверу {server.name}: {e}")
            count = 9999

        if count < min_count:
            selected = server
            min_count = count

    if selected:
        logger.info(f"Выбран наименее загруженный сервер: {selected.name} ({min_count} юзеров)")
        return selected

    logger.warning("Все серверы недоступны. Возвращаю первый активный как fallback")
    return servers.first()


def get_least_loaded_server_by_country(name: str):
    # Сначала пытаемся найти по стране
    server = VPNServer.objects.filter(is_active=True, name=name).first()
    
    if server:
        return server

    # Если не нашли — берём любой активный
    return VPNServer.objects.filter(is_active=True).first()
