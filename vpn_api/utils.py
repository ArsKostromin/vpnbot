import requests
from dateutil.relativedelta import relativedelta


import logging

logger = logging.getLogger(__name__)

def create_vless(server, uuid: str) -> dict:
    """
    Создаёт пользователя на сервере (через FastAPI),
    и возвращает VLESS-ссылку, сгенерированную на стороне Django.
    """
    try:
        # Шлём UUID на FastAPI
        response = requests.post(
            f"{server.api_url}/vless",
            json={"uuid": str(uuid)},
            timeout=10
        )
        response.raise_for_status()
        data = response.json()

        if not data.get("success"):
            logger.warning(f"FastAPI вернул ошибку: {data}")
            return {"success": False, "message": data.get("message", "Unknown error from FastAPI")}

        # Генерим ссылку на своей стороне
        vless_link = generate_vless_link(str(uuid), server.domain, server.name)

        return {"success": True, "vless_link": vless_link}

    except Exception as e:
        logger.error(f"Ошибка при создании пользователя на сервере: {e}")
        return {"success": False, "message": str(e)}


def delete_vless(server, uuid: str) -> bool:
    """
    Удаляет VLESS пользователя через FastAPI на указанном сервере.
    Возвращает True, если успех.
    """
    try:
        response = requests.delete(
            f"{server.api_url}/vless",
            json={"uuid": str(uuid)},
            timeout=10
        )
        response.raise_for_status()
        data = response.json()
        return data.get("success", False)
    except requests.RequestException as e:
        print(f"[delete_vless] Запрос провалился: {e}")
        return False


def get_duration_delta(duration_code: str):
    """
    Возвращает timedelta или relativedelta для длительности подписки.
    """
    duration_map = {
        '1m': relativedelta(months=1),
        '3m': relativedelta(months=3),
        '6m': relativedelta(months=6),
        '1y': relativedelta(years=1),
    }
    return duration_map.get(duration_code)


def generate_vless_link(uuid: str, server_domain: str, server_name: str) -> str:
    """
    Генерирует VLESS-ссылку по заданному UUID и данным сервера.
    """
    return (
        f"vless://{uuid}@{server_domain}:443"
        f"?encryption=none&security=tls&type=ws"
        f"&host={server_domain}&path=%2Fws"
        f"#{server_name}"
    )