import requests
from dateutil.relativedelta import relativedelta


def create_vless(server, uuid: str) -> dict:
    """
    Создаёт VLESS пользователя через FastAPI на указанном сервере.
    Возвращает dict с ключами 'success', 'vless_link', 'message'.
    """
    try:
        response = requests.post(
            f"{server.api_url}/vless",
            json={"uuid": str(uuid)},
            timeout=10
        )
        response.raise_for_status()
        data = response.json()
        if data.get("success"):
            return {"success": True, "vless_link": data.get("vless_link")}
        return {"success": False, "message": data.get("message")}
    except Exception as e:
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
