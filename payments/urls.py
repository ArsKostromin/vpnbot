#payments/urls
from django.urls import path
from payments import views

urlpatterns = [
    path('create-payment/', views.create_payment, name='create-payment'),
    path('payment-result/', views.payment_result, name='payment-result'),
    path('payment-success/', views.success_payment, name='payment-success'),
    path('payment-fail/', views.fail_payment, name='payment-fail'),
    path('api/crypto/webhook/', views.crypto_webhook, name='crypto_webhook'),
    path('api/crypto/create/', views.CreateCryptoPaymentAPIView.as_view(), name='create_crypto_payment'),
    path("payments/stars/", views.StarPaymentAPIView.as_view(), name="star-payment"),
]
