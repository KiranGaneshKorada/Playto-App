from rest_framework import serializers
from merchants.models import Merchant, BankAccount
from ledger.models import LedgerEntry
from payouts.models import Payout

def format_inr(paise):
    if paise is None:
        return "₹0.00"
    rupees_str = f"{abs(paise) / 100:.2f}"
    integer_part, decimal_part = rupees_str.split('.')
    if len(integer_part) > 3:
        last_three = integer_part[-3:]
        other_numbers = integer_part[:-3]
        chunks = []
        for i in range(len(other_numbers), 0, -2):
            start = max(i-2, 0)
            chunks.append(other_numbers[start:i])
        chunks.reverse()
        formatted_integer = ','.join(chunks) + ',' + last_three
    else:
        formatted_integer = integer_part
    
    sign = "-" if paise < 0 else ""
    return f"{sign}₹{formatted_integer}.{decimal_part}"

class MerchantBalanceSerializer(serializers.ModelSerializer):
    merchant_id = serializers.UUIDField(source='id')
    merchant_name = serializers.CharField(source='name')
    
    available_balance_paise = serializers.IntegerField(read_only=True)
    held_balance_paise = serializers.IntegerField(read_only=True)
    total_balance_paise = serializers.IntegerField(read_only=True)
    
    available_balance_inr = serializers.SerializerMethodField()
    held_balance_inr = serializers.SerializerMethodField()
    total_balance_inr = serializers.SerializerMethodField()

    class Meta:
        model = Merchant
        fields = [
            'merchant_id', 'merchant_name', 
            'available_balance_paise', 'held_balance_paise', 'total_balance_paise',
            'available_balance_inr', 'held_balance_inr', 'total_balance_inr'
        ]

    def get_available_balance_inr(self, obj):
        return format_inr(obj.available_balance_paise)

    def get_held_balance_inr(self, obj):
        return format_inr(obj.held_balance_paise)

    def get_total_balance_inr(self, obj):
        return format_inr(obj.total_balance_paise)

class BankAccountSerializer(serializers.ModelSerializer):
    account_number = serializers.SerializerMethodField()

    class Meta:
        model = BankAccount
        fields = ['id', 'bank_name', 'account_holder_name', 'account_number', 'ifsc_code', 'is_primary', 'is_active']

    def get_account_number(self, obj):
        if obj.account_number:
            return '*' * max(0, len(obj.account_number) - 4) + obj.account_number[-4:]
        return ''

class LedgerEntrySerializer(serializers.ModelSerializer):
    amount_inr = serializers.SerializerMethodField()

    class Meta:
        model = LedgerEntry
        fields = ['id', 'entry_type', 'amount_paise', 'amount_inr', 'description', 'reference_id', 'created_at']

    def get_amount_inr(self, obj):
        return format_inr(obj.amount_paise)

class PayoutCreateSerializer(serializers.Serializer):
    amount_paise = serializers.IntegerField(
        min_value=100, # minimum ₹1
        max_value=1000000000 # max ₹1 crore (1,00,00,000 INR = 100,00,00,000 Paise)
    )
    bank_account_id = serializers.UUIDField()

    def validate_bank_account_id(self, value):
        merchant = self.context.get('merchant')
        if not merchant:
            raise serializers.ValidationError("Merchant context is required for validation.")
        
        try:
            bank_account = BankAccount.objects.get(id=value, merchant=merchant)
        except BankAccount.DoesNotExist:
            raise serializers.ValidationError("Bank account not found or does not belong to the merchant.")
            
        if not bank_account.is_active:
            raise serializers.ValidationError("Bank account is inactive.")
            
        return value

class PayoutSerializer(serializers.ModelSerializer):
    merchant_id = serializers.UUIDField(source='merchant.id', read_only=True)
    bank_account = BankAccountSerializer(read_only=True)
    amount_inr = serializers.SerializerMethodField()
    state_display = serializers.CharField(source='get_state_display', read_only=True)

    class Meta:
        model = Payout
        fields = [
            'id', 'merchant_id', 'bank_account', 
            'amount_paise', 'amount_inr', 'state', 'state_display', 
            'attempts', 'failure_reason', 'processing_started_at', 
            'completed_at', 'created_at', 'updated_at'
        ]
        read_only_fields = fields

    def get_amount_inr(self, obj):
        return format_inr(obj.amount_paise)
