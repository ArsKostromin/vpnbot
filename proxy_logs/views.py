from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import ProxyLog
from user.models import VPNUser
from django.utils.dateparse import parse_datetime
import re

class ProxyLogReceiver(APIView):
    def post(self, request):
        data = request.data
        raw_log = data.get("log")
        remote_ip = data.get("ip")
        timestamp = parse_datetime(data.get("timestamp"))

        # Попытка извлечь UUID из email-подобной строки
        uuid_match = re.search(r'[a-f0-9\-]{36}', raw_log)
        user = None
        domain = None
        status_code = None
        bytes_sent = None

        if uuid_match:
            try:
                user = VPNUser.objects.get(uuid=uuid_match.group(0))
            except VPNUser.DoesNotExist:
                pass

        # Попытка вытащить домен из лога, если лог выглядит как squid лог
        parts = raw_log.split()
        if len(parts) >= 7:
            try:
                domain = parts[6]
                status_code = parts[3]
                bytes_sent = int(parts[4])
            except Exception:
                pass

        ProxyLog.objects.create(
            user=user,
            timestamp=timestamp,
            raw_log=raw_log,
            remote_ip=remote_ip,
            domain=domain,
            status=status_code,
            bytes_sent=bytes_sent
        )

        return Response({"ok": True}, status=status.HTTP_201_CREATED)
