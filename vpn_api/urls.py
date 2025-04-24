from django.urls import path
from .views import BuySubscriptionView, SubscriptionPlanListView

urlpatterns = [
    path('plans/', SubscriptionPlanListView.as_view(), name='subscription-plans'),
    path('buy/', BuySubscriptionView.as_view(), name='buy-subscription'),
]
