import json
import os
import subprocess

CONFIG_PATH = "/usr/local/etc/xray/config.json"

def apply_vless_on_server(user_uuid):
    # Загружаем текущий конфиг
    with open(CONFIG_PATH, "r") as f:
        config = json.load(f)

    # Проверка, есть ли UUID уже в списке
    existing_ids = [client.get("id") for client in config["inbounds"][0]["settings"]["clients"]]
    if user_uuid in existing_ids:
        print(f"UUID {user_uuid} уже добавлен.")
        return

    # Добавляем нового клиента
    config["inbounds"][0]["settings"]["clients"].append({
        "id": user_uuid,
        "level": 0
    })

    # Сохраняем конфиг
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=2)

    # Перезапускаем Xray с контролем ошибок
    try:
        subprocess.run(["sudo", "/usr/local/bin/restart-xray.sh"], check=True)
        print("Xray успешно перезапущен.")
    except subprocess.CalledProcessError as e:
        print("Ошибка при перезапуске Xray:", e)
