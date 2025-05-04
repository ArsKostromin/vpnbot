import re
from django.core.management.base import BaseCommand
from proxy_logs.models import ProxyLog

LOG_PATH = "/app/access.log"

LOG_PATTERN = re.compile(
    r'(?P<unix_ts>\d+\.\d+)\s+(?P<duration>\d+)\s+(?P<ip>[^\s]+)\s+(?P<status>[^\s]+)\s+(?P<bytes>\d+)\s+CONNECT\s+(?P<domain>[^:]+)'
)

from datetime import datetime

class Command(BaseCommand):
    help = "Импортирует логи из access.log Squid в базу данных"

    def handle(self, *args, **kwargs):
        with open(LOG_PATH, "r") as f:
            lines = f.readlines()

        count = 0
        for line in lines:
            match = LOG_PATTERN.search(line)
            if not match:
                continue

            data = match.groupdict()
            timestamp = datetime.fromtimestamp(float(data["unix_ts"]))

            ProxyLog.objects.create(
                timestamp=timestamp,
                raw_log=line.strip(),
                remote_ip=data["ip"],
                domain=data["domain"],
                status=data["status"],
                bytes_sent=int(data["bytes"])
            )
            count += 1

        self.stdout.write(self.style.SUCCESS(f"Импортировано {count} логов."))
