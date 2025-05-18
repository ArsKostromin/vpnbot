#config
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('vpn/', include('vpn_api.urls')),
    path('user/', include('user.urls')),
    path('payments/', include('payments.urls')),
    path('coupon/', include('coupon.urls')),
    path("proxylogs/", include("proxy_logs.urls")),
]
