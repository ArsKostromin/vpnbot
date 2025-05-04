import re
from datetime import datetime
from user.models import VPNUser
from vpn_api.models import ProxyLog

LOG_PATTERN = re.compile(
    r"(?P<timestamp>\d+\.\d+)\s+(?P<duration>\d+)\s+(?P<ip>[\d.]+)\s+(?P<status>[A-Z_\/0-9]+)\s+(?P<bytes>\d+)\s+CONNECT\s+(?P<domain>[\w\.\-]+):443"
)

def parse_log_line(log_line):
    match = LOG_PATTERN.search(log_line)
    if not match:
        return None

    data = match.groupdict()
    try:
        user = VPNUser.objects.get(current_ip=data['ip'])
    except VPNUser.DoesNotExist:
        user = None

    # Создаём лог
    ProxyLog.objects.create(
        user=user,
        raw_log=log_line.strip(),
        remote_ip=data['ip'],
        domain=data['domain'],
        status=data['status'],
        bytes_sent=int(data['bytes']),
    )

    return data
