from django.urls import path
from .views import ApplyCouponView, generate_promo_code

urlpatterns = [
    path("apply-coupon/", ApplyCouponView.as_view(), name="apply-coupon"),
    path("generate_promo/", generate_promo_code, name="generate_promo")
]
