from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import ProxyLog
from user.models import VPNUser
from django.utils.dateparse import parse_datetime

class ProxyLogReceiver(APIView):
    def post(self, request):
        data = request.data

        uuid = data.get("uuid")
        remote_ip = data.get("ip")
        hostname = data.get("host")
        destination = data.get("destination")
        raw_log = data.get("raw_log")
        timestamp = parse_datetime(data.get("timestamp"))

        user = None
        if uuid and uuid != "unknown":
            try:
                user = VPNUser.objects.get(uuid=uuid)
            except VPNUser.DoesNotExist:
                pass

        # Пробуем вытянуть статус и байты из raw_log, если лог похож на squid
        status_code = None
        bytes_sent = None
        parts = raw_log.split()
        if len(parts) >= 5:
            try:
                status_code = parts[3]
                bytes_sent = int(parts[4])
            except Exception:
                pass

        ProxyLog.objects.create(
            user=user,
            timestamp=timestamp,
            raw_log=raw_log,
            remote_ip=remote_ip,
            domain=destination,
            status=status_code,
            bytes_sent=bytes_sent,
            hostname=hostname
        )

        return Response({"ok": True}, status=status.HTTP_201_CREATED)
