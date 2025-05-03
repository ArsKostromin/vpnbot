import json
import os

CONFIG_PATH = "/usr/local/etc/xray/config.json"

def apply_vless_on_server(user_uuid):
    with open(CONFIG_PATH, "r") as f:
        config = json.load(f)

    client_entry = {
        "id": user_uuid,
        "level": 0
    }

    config["inbounds"][0]["settings"]["clients"].append(client_entry)

    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=2)

    os.system("systemctl restart xray")
