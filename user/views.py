# views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import VPNUser

class RegisterUserView(APIView):
    def post(self, request):
        telegram_id = request.data.get("telegram_id")

        if not telegram_id:
            return Response({"error": "telegram_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        user, created = VPNUser.objects.get_or_create(telegram_id=telegram_id)

        # Если пользователь уже есть, но его аккаунт заблокирован
        if not created and user.is_banned:
            return Response({"error": "Пользователь заблокирован"}, status=status.HTTP_403_FORBIDDEN)

        return Response({
            "created": created,
            "link_code": user.link_code, 
        }, status=status.HTTP_201_CREATED)