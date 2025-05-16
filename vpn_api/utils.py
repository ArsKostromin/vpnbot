import requests

FASTAPI_VLESS_ENDPOINT = "http://159.198.77.150:8000/api/v1/vless"

def create_vless(uuid: str) -> str | None:
    """
    Создаёт VLESS пользователя через FastAPI. Возвращает ссылку, если успех.
    """
    try:
        response = requests.post(FASTAPI_VLESS_ENDPOINT, json={"uuid": str(uuid)}, timeout=10)
        response.raise_for_status()
        data = response.json()
        if data.get("success"):
            return data.get("vless_link")
        else:
            print(f"[create_vless] Ошибка: {data.get('message')}")
            return None
    except requests.RequestException as e:
        print(f"[create_vless] Запрос провалился: {e}")
        return None


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
