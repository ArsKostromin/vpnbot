from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework.decorators import api_view
from rest_framework import status
from user.models import VPNUser
from .services import apply_coupon_to_user, generate_coupon_for_user


class ApplyCouponView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        code = request.data.get("code", "").strip()
        telegram_id = request.data.get("telegram_id")

        if not telegram_id:
            return Response({"error": "telegram_id обязателен"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = VPNUser.objects.get(telegram_id=telegram_id)
        except VPNUser.DoesNotExist:
            return Response({"error": "Пользователь не найден"}, status=status.HTTP_404_NOT_FOUND)

        # Проверка на бан пользователя
        if user.is_banned:
            return Response({
                "error": "Ваш аккаунт заблокирован",
                "ban_reason": user.ban_reason or "Причина не указана"
            }, status=status.HTTP_403_FORBIDDEN)

        if not code:
            return Response({"detail": "Промокод не указан."}, status=status.HTTP_400_BAD_REQUEST)

        result = apply_coupon_to_user(user, code, request)

        # Вставляем ссылку в ответ, если она есть
        response_data = result.get("data", {})
        if hasattr(user, "subscription") and user.subscription:
            response_data["vless"] = user.subscription.vless

        return Response(response_data, status=result["status"])


@api_view(['POST'])
def generate_promo_code(request):
    telegram_id = request.data.get("telegram_id")

    if not telegram_id:
        return Response({"error": "telegram_id is required"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        user = VPNUser.objects.get(telegram_id=telegram_id)
    except VPNUser.DoesNotExist:
        return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)

    # Проверка на бан пользователя
    if user.is_banned:
        return Response({
            "error": "Ваш аккаунт заблокирован",
            "ban_reason": user.ban_reason or "Причина не указана"
        }, status=status.HTTP_403_FORBIDDEN)

    # Проверка: выдавался ли уже промокод
    if user.promo_code_issued:
        return Response({"error": "Промокод уже был выдан ранее"}, status=status.HTTP_400_BAD_REQUEST)

    # Логика генерации промокода вынесена
    promo_code = generate_coupon_for_user(user)
    user.promo_code_issued = True
    user.save(update_fields=["promo_code_issued"])

    return Response({"promo_code": promo_code})
