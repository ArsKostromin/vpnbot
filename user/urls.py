from django.contrib import admin
from django.urls import path, include
from django.urls import re_path
from .views import RegisterUserView, UserSubscriptionsAPIView, UserBalanceAndLinkAPIView, ToggleAutoRenewAPIView


# urls.py
urlpatterns = [
    path('api/register/', RegisterUserView.as_view()),
    path('user-subscriptions/<int:telegram_id>/', UserSubscriptionsAPIView.as_view(), name='user-subscriptions'),
    path('user-info/<int:telegram_id>/', UserBalanceAndLinkAPIView.as_view(), name='user-info'),
    path('toggle-autorenew/<int:subscription_id>/', ToggleAutoRenewAPIView.as_view(), name='toggle-autorenew'),
]
