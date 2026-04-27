from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.db import connection
import redis
from django.conf import settings

class HealthCheckView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        response_data = {
            "status": "ok",
            "database": "connected",
            "redis": "connected",
            "timestamp": timezone.now().isoformat()
        }
        
        # Check Database
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
        except Exception:
            response_data["status"] = "error"
            response_data["database"] = "error"
            
        # Check Redis
        try:
            r = redis.from_url(settings.CELERY_BROKER_URL)
            r.ping()
        except Exception:
            response_data["status"] = "error"
            response_data["redis"] = "error"
            
        if response_data["status"] == "error":
            return Response(response_data, status=status.HTTP_503_SERVICE_UNAVAILABLE)
            
        return Response(response_data)

from merchants.models import Merchant, BankAccount
from ledger.models import LedgerEntry
from payouts.models import Payout
from payouts.serializers import (
    MerchantBalanceSerializer,
    BankAccountSerializer,
    LedgerEntrySerializer,
    PayoutCreateSerializer,
    PayoutSerializer
)
from payouts.services import create_payout, InsufficientFundsError

class BaseMerchantAPIView(APIView):
    """
    Helper to get the authenticated merchant.
    Assuming request.user is linked to exactly one Merchant.
    """
    def get_merchant(self, request):
        if not request.user.is_authenticated:
            return None
        return getattr(request.user, 'merchant', None)

class BalanceView(BaseMerchantAPIView):
    def get(self, request):
        merchant = self.get_merchant(request)
        if not merchant:
            return Response({'error': 'Unauthorized or no merchant linked'}, status=status.HTTP_401_UNAUTHORIZED)
            
        serializer = MerchantBalanceSerializer(merchant)
        return Response(serializer.data)

class BankAccountListView(BaseMerchantAPIView):
    def get(self, request):
        merchant = self.get_merchant(request)
        if not merchant:
            return Response({'error': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)
            
        accounts = BankAccount.objects.filter(merchant=merchant, is_active=True)
        serializer = BankAccountSerializer(accounts, many=True)
        return Response(serializer.data)

class PayoutCreateView(BaseMerchantAPIView):
    def post(self, request):
        merchant = self.get_merchant(request)
        if not merchant:
            return Response({'error': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)
            
        idempotency_key = request.META.get('HTTP_IDEMPOTENCY_KEY')
        if not idempotency_key:
            return Response({'error': 'Idempotency-Key header is required'}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            import uuid
            uuid.UUID(str(idempotency_key))
        except ValueError:
            return Response({'error': 'Idempotency-Key must be a valid UUID'}, status=status.HTTP_400_BAD_REQUEST)
            
        serializer = PayoutCreateSerializer(data=request.data, context={'merchant': merchant})
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            payout, response_body, status_code, was_duplicate = create_payout(
                merchant=merchant,
                amount_paise=serializer.validated_data['amount_paise'],
                bank_account_id=serializer.validated_data['bank_account_id'],
                idempotency_key_str=idempotency_key
            )
            
            response = Response(response_body, status=status_code)
            if was_duplicate:
                response['X-Idempotent-Replayed'] = 'true'
            return response
            
        except InsufficientFundsError as e:
            return Response({
                'error': 'insufficient_funds',
                'available_paise': e.available,
                'requested_paise': e.requested,
                'message': 'Insufficient available balance'
            }, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

class PayoutListView(BaseMerchantAPIView):
    def get(self, request):
        merchant = self.get_merchant(request)
        if not merchant:
            return Response({'error': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)
            
        payouts = Payout.objects.filter(merchant=merchant) # todo -> use select_related('bank_account') (joining the bank account table also reduces the no of queries)
        
        state_filter = request.query_params.get('state')
        if state_filter:
            payouts = payouts.filter(state=state_filter)
            
        limit = int(request.query_params.get('limit', 20))
        payouts = payouts.order_by('-created_at')[:limit]
        
        serializer = PayoutSerializer(payouts, many=True)
        return Response(serializer.data)

class PayoutDetailView(BaseMerchantAPIView):
    def get(self, request, payout_id):
        merchant = self.get_merchant(request)
        if not merchant:
            return Response({'error': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)
            
        payout = get_object_or_404(Payout, id=payout_id, merchant=merchant)
        serializer = PayoutSerializer(payout)
        return Response(serializer.data)

class LedgerView(BaseMerchantAPIView):
    def get(self, request):
        merchant = self.get_merchant(request)
        if not merchant:
            return Response({'error': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)
            
        entries = LedgerEntry.objects.filter(merchant=merchant).order_by('-created_at')[:50]
        serializer = LedgerEntrySerializer(entries, many=True)
        return Response(serializer.data)
