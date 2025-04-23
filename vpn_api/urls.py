from django.urls import path
from .views import SelectVPNTypeView, SelectDurationView, PurchaseSubscriptionView

urlpatterns = [
    path('select-type/', SelectVPNTypeView.as_view(), name='select-vpn-type'),
    path('select-duration/', SelectDurationView.as_view(), name='select-vpn-duration'),
    path('purchase/', PurchaseSubscriptionView.as_view(), name='purchase-vpn'),
]