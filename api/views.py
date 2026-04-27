from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny # For ease of development/testing based on user context
from django.shortcuts import get_object_or_404
from merchants.models import Merchant
from payouts.models import Payout
from payouts.services import request_payout, InsufficientFundsError, DuplicateRequestError
from payouts.serializers import MerchantBalanceSerializer, PayoutSerializer, PayoutCreateSerializer

class MerchantViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Merchant.objects.all()
    serializer_class = MerchantBalanceSerializer
    permission_classes = [AllowAny] # Using AllowAny since auth wasn't specifically requested

    @action(detail=True, methods=['get'])
    def balance(self, request, pk=None):
        merchant = self.get_object()
        serializer = self.get_serializer(merchant)
        return Response(serializer.data)

class PayoutViewSet(viewsets.ModelViewSet):
    serializer_class = PayoutSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        merchant_id = self.kwargs.get('merchant_pk')
        if merchant_id:
            return Payout.objects.filter(merchant_id=merchant_id).order_by('-created_at')
        return Payout.objects.all().order_by('-created_at')

    def create(self, request, merchant_pk=None):
        merchant = get_object_or_404(Merchant, pk=merchant_pk)
        serializer = PayoutCreateSerializer(data=request.data, context={'merchant': merchant})
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        amount_paise = serializer.validated_data['amount_paise']
        bank_account_id = serializer.validated_data.get('bank_account_id')
        from payouts.services import create_payout, InsufficientFundsError
        import uuid

        idempotency_key = serializer.validated_data.get('idempotency_key', str(uuid.uuid4()))

        try:
            payout, response_body, response_status, was_duplicate = create_payout(
                merchant=merchant,
                amount_paise=amount_paise,
                bank_account_id=bank_account_id,
                idempotency_key_str=idempotency_key
            )
            return Response(response_body, status=response_status)
        
        except InsufficientFundsError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
