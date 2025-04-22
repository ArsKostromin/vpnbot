# import uuid
# import requests
# from rest_framework.views import APIView
# from rest_framework.response import Response
# from user.models import VPNUser




# def send_message(chat_id, text):
#     url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
#     requests.post(url, data={"chat_id": chat_id, "text": text})


# class TelegramWebhookView(APIView):
#     def post(self, request):
#         data = request.data

#         # Проверим, что это обычное сообщение (а не callback, например)
#         message = data.get("message")
#         if not message:
#             return Response({"ok": True})  # просто игнорируем

#         telegram_id = message["from"]["id"]
#         chat_id = message["chat"]["id"]

#         # Получаем или создаём пользователя
#         user, created = VPNUser.objects.get_or_create(telegram_id=telegram_id)

#         # Если ключ ещё не создан — создаём
#         if not user.vpn_key:
#             key = str(uuid.uuid4())
#             user.vpn_key = f"vless://{key}@vpn.domain.com:443?flow=xtls-rprx-vision&security=reality&type=tcp&alpn=http/1.1&sni=example.com&fp=chrome&pbk=EXAMPLE_PUBLIC_KEY#VPN"
#             user.save()

#         # Отправляем пользователю ключ
#         send_message(chat_id, f"👋 Привет!\nВот твой VPN-ключ:\n\n<code>{user.vpn_key}</code>",)

#         return Response({"ok": True})
