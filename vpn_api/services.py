# services.py

from .utils import get_duration_delta

def extend_subscription(subscription, plan):
    delta = get_duration_delta(plan.duration)
    if not delta:
        raise ValueError("Неизвестная длительность плана")

    subscription.end_date += delta
    subscription.save()
    return subscription
