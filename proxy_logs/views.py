import re
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import ProxyLog
from user.models import VPNUser
from django.utils.dateparse import parse_datetime
from uuid import UUID

class ProxyLogReceiver(APIView):
    def post(self, request):
        data = request.data

        raw_log = data.get("raw_log")
        remote_ip = data.get("ip")
        destination = data.get("destination")
        timestamp = parse_datetime(data.get("timestamp"))
        uuid_str = data.get("uuid")

        # Если UUID не пришёл — пробуем вытащить из raw_log
        if not uuid_str and raw_log:
            uuid_match = re.search(r'[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}', raw_log)
            if uuid_match:
                uuid_str = uuid_match.group(0)

        user = None
        if uuid_str and uuid_str != "unknown":
            try:
                # Конвертируем в настоящий UUID (важно!)
                uuid_obj = UUID(uuid_str)
                subscription = Subscription.objects.get(uuid=email_from_log)
                user = subscription.user
            except (ValueError, VPNUser.DoesNotExist):
                pass

        # Парсим статус и байты, если лог похож на Squid
        status_code = None
        bytes_sent = None
        if raw_log:
            parts = raw_log.split()
            if len(parts) >= 5:
                try:
                    status_code = parts[3].split("/")[1] if "/" in parts[3] else None
                    bytes_sent = int(parts[4])
                except Exception:
                    pass

        ProxyLog.objects.create(
            user=user,
            timestamp=timestamp,
            raw_log=raw_log or "",
            remote_ip=remote_ip,
            domain=destination,
            status=status_code,
            bytes_sent=bytes_sent,
        )

        return Response({"ok": True}, status=status.HTTP_201_CREATED)
