import requests
from dateutil.relativedelta import relativedelta

FASTAPI_VLESS_ENDPOINT = "http://159.198.77.150:8000/api/v1/vless"

def create_vless(uuid: str) -> dict:
    """
    Создаёт VLESS пользователя через FastAPI. Возвращает dict с ключами 'success', 'vless_link', 'message'.
    """
    try:
        response = requests.post(
            FASTAPI_VLESS_ENDPOINT,
            json={"uuid": str(uuid)},
            timeout=10
        )
        response.raise_for_status()
        data = response.json()
        if data.get("success"):
            return {"success": True, "vless_link": data.get("vless_link")}
        else:
            print(f"[create_vless] Ошибка от FastAPI: {data.get('message')}")
            return {"success": False, "message": data.get("message")}
    except requests.RequestException as e:
        print(f"[create_vless] Сетевая ошибка: {e}")
        return {"success": False, "message": str(e)}


def delete_vless(uuid: str) -> bool:
    """
    Удаляет VLESS пользователя через FastAPI. Возвращает True, если успех.
    """
    try:
        response = requests.delete(FASTAPI_VLESS_ENDPOINT, json={"uuid": uuid}, timeout=10)
        response.raise_for_status()
        data = response.json()
        return data.get("success", False)
    except requests.RequestException as e:
        print(f"[delete_vless] Запрос провалился: {e}")
        return False


def get_duration_delta(duration_code: str):
    duration_map = {
        '1m': relativedelta(months=1),
        '3m': relativedelta(months=3),
        '6m': relativedelta(months=6),
        '1y': relativedelta(years=1),
    }
    return duration_map.get(duration_code)
