from django.urls import path
from .views import ProxyLogReceiver

# urls.py
urlpatterns = [
    path('receive-log/', ProxyLogReceiver.as_view(), name='receive_log'),
]
