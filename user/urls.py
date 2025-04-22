from django.contrib import admin
from django.urls import path, include
from django.urls import re_path
from .views import RegisterUserView


# urls.py
urlpatterns = [
    path('api/register/', RegisterUserView.as_view()),
]
