from django.urls import path
from payments import views

urlpatterns = [
    path('create-payment/', views.create_payment, name='create-payment'),
    path('payment-result/', views.payment_result, name='payment-result'),
    path('payment-success/', views.success_payment, name='payment-success'),
    path('payment-fail/', views.fail_payment, name='payment-fail'),
]
