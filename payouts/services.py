import logging
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone
from datetime import timedelta
from merchants.models import Merchant, BankAccount
from ledger.models import LedgerEntry
from .models import Payout, IdempotencyKey

logger = logging.getLogger(__name__)

class PayoutError(Exception):
    pass

class InsufficientFundsError(PayoutError):
    def __init__(self, available, requested):
        self.available = available
        self.requested = requested
        super().__init__(f"Insufficient funds: available {available}, requested {requested}")

class InvalidTransitionError(PayoutError):
    pass

class PayoutNotFoundError(PayoutError):
    pass


def hold_funds(merchant, amount_paise):
    """
    Atomically check balance and ensure we have enough funds.
    The Payout object itself acts as the hold record.
    """
    with transaction.atomic():
        # 1. Use select_for_update() on the merchant's LedgerEntry rows
        # We evaluate the queryset to actually lock the rows
        list(LedgerEntry.objects.select_for_update().filter(merchant=merchant).values('id'))
        
        # 2. Compute available balance at DB level
        balance_info = LedgerEntry.objects.balance_for(merchant)
        available_balance = balance_info['net']
        
        # 3. Compute currently held amount from active payouts
        held_amount = Payout.objects.filter(
            merchant=merchant,
            state__in=[Payout.PENDING, Payout.PROCESSING]
        ).aggregate(Sum('amount_paise'))['amount_paise__sum'] or 0
        
        # 4. Check balance
        if available_balance - held_amount < amount_paise:
            # 5. If not enough: raise InsufficientFundsError
            raise InsufficientFundsError(available=available_balance - held_amount, requested=amount_paise)
            
        # 6. If yes: return True
        return True


def release_held_funds(payout):
    """
    On payout failure, return held funds.
    Since hold_funds does not write a debit, this function
    just relies on the state transition to release the virtual hold.
    """
    pass


def finalize_payout(payout):
    """
    On payout success, record the final debit.
    """
    with transaction.atomic():
        if payout.bank_account:
            last4 = payout.bank_account.account_number[-4:] if payout.bank_account.account_number else 'XXXX'
            bank_name = payout.bank_account.bank_name
        else:
            last4 = 'XXXX'
            bank_name = 'Unknown Bank'
            
        LedgerEntry.record_debit(
            merchant=payout.merchant,
            amount_paise=payout.amount_paise,
            description=f'Payout to {bank_name} ****{last4}',
            reference_id=payout.id
        )


def create_payout(merchant, amount_paise, bank_account_id, idempotency_key_str):
    """
    Full payout creation with idempotency check.
    Returns: (payout, response_body, status_code, was_duplicate)
    """
    # 1. Lock merchant first, then check idempotency inside the lock.
    # This single check is fully race-free: by the time we hold the merchant
    # lock, any concurrent winner has committed its IdempotencyKey row.
    with transaction.atomic():
        merchant_locked = Merchant.objects.select_for_update().get(id=merchant.id)

        existing_key = IdempotencyKey.get_valid(merchant_locked, idempotency_key_str)
        if existing_key and existing_key.payout_id:
            return (existing_key.payout, existing_key.response_body,
                    existing_key.response_status, True)

        bank_account = BankAccount.objects.get(id=bank_account_id, merchant=merchant_locked)

        # a. hold_funds
        hold_funds(merchant_locked, amount_paise)
        
        # b. Create Payout object
        payout = Payout.objects.create(
            merchant=merchant_locked,
            bank_account=bank_account,
            amount_paise=amount_paise,
            state=Payout.PENDING
        )
        
        # c. Create or Update IdempotencyKey (if it was expired, we overwrite it)
        ik, _ = IdempotencyKey.objects.update_or_create(
            merchant=merchant_locked,
            key=idempotency_key_str,
            defaults={
                'payout': payout,
                'expires_at': timezone.now() + timedelta(hours=24)
            }
        )
        
        # d. Build response_body dict (simulating the serializer structure)
        # We'll use the actual serializer to keep it identical to API responses
        from payouts.serializers import PayoutSerializer
        response_body = PayoutSerializer(payout).data
        
        # e. Save IdempotencyKey.response_body
        ik.response_body = response_body
        ik.response_status = 201
        ik.save(update_fields=['response_body', 'response_status'])
        
    # 3. Enqueue Celery task
    from .tasks import process_payout
    process_payout.delay(str(payout.id))
    
    # 4. Return
    return (payout, response_body, 201, False)
