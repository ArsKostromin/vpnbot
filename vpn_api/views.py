from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from .serializers import SelectTypeSerializer, SelectDurationSerializer, PurchaseSubscriptionSerializer


class SelectVPNTypeView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = SelectTypeSerializer(data=request.data)
        if serializer.is_valid():
            return Response({"message": "Тип VPN выбран", "vpn_type": serializer.validated_data['vpn_type']})
        return Response(serializer.errors, status=400)


class SelectDurationView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = SelectDurationSerializer(data=request.data)
        if serializer.is_valid():
            return Response({"message": "Длительность выбрана", "duration": serializer.validated_data['duration']})
        return Response(serializer.errors, status=400)


class PurchaseSubscriptionView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = PurchaseSubscriptionSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            subscription = serializer.save()
            return Response({
                "message": "Подписка успешно оформлена!",
                "subscription_id": subscription.id,
                "vpn_key": subscription.vpn_key.key,
                "expires": subscription.end_date
            })
        return Response(serializer.errors, status=400)
