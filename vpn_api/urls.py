from django.urls import path
from .views import BuySubscriptionView, SubscriptionPlanListView, CountriesPlanListView

urlpatterns = [
    path('plans/', SubscriptionPlanListView.as_view(), name='subscription-plans'),
    path('buy/', BuySubscriptionView.as_view(), name='buy-subscription'),
    path('countries/', CountriesPlanListView.as_view(), name='countries'),
    # path('config/vless/', VLESSConfigView.as_view(), name='vless-config'),
]
