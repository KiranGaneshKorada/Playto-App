import threading
import uuid
from django.test import TransactionTestCase
from merchants.models import Merchant
from ledger.models import LedgerEntry
from payouts.models import Payout
from payouts.services import create_payout, InsufficientFundsError
from payouts.tests.factories import MerchantFactory, BankAccountFactory, LedgerEntryFactory

class ConcurrencyTests(TransactionTestCase):
    def setUp(self):
        self.merchant = MerchantFactory()
        self.bank_account = BankAccountFactory(merchant=self.merchant)
        # Give merchant 10,000 available (1,000,000 paise)
        LedgerEntryFactory(merchant=self.merchant, entry_type=LedgerEntry.CREDIT, amount_paise=1000000)

    def test_concurrent_payouts_only_one_succeeds(self):
        # We need to simulate two simultaneous API calls. We'll use threads.
        exceptions = []
        payouts_created = []

        def worker():
            try:
                payout, _, _, _ = create_payout(
                    merchant=self.merchant,
                    amount_paise=600000, # ₹6,000
                    bank_account_id=self.bank_account.id,
                    idempotency_key_str=str(uuid.uuid4())
                )
                payouts_created.append(payout)
            except Exception as e:
                exceptions.append(e)
            finally:
                from django.db import connection
                connection.close()

        t1 = threading.Thread(target=worker)
        t2 = threading.Thread(target=worker)

        t1.start()
        t2.start()

        t1.join()
        t2.join()

        # Assert: Exactly one payout is created in 'pending' state
        self.assertEqual(len(payouts_created), 1)
        self.assertEqual(payouts_created[0].state, Payout.PENDING)

        # Assert: The other raises InsufficientFundsError
        self.assertEqual(len(exceptions), 1)
        self.assertIsInstance(exceptions[0], InsufficientFundsError)

        # Refresh merchant balance
        self.merchant.refresh_from_db()
        
        # Assert: Merchant balance after = ₹4,000 available + ₹6,000 held = ₹10,000 total
        self.assertEqual(self.merchant.available_balance_paise, 400000)
        self.assertEqual(self.merchant.held_balance_paise, 600000)
        self.assertEqual(self.merchant.total_balance_paise, 1000000)

    def test_balance_invariant_always_holds(self):
        # Setup: Merchant with various credits and a mix of completed/failed/pending payouts.
        # Initial credit of 1,000,000 paise (₹10k) already exists.
        LedgerEntryFactory(merchant=self.merchant, entry_type=LedgerEntry.CREDIT, amount_paise=500000)
        LedgerEntryFactory(merchant=self.merchant, entry_type=LedgerEntry.CREDIT, amount_paise=200000)
        
        # Make a completed payout (creates debit)
        from payouts.services import finalize_payout
        p1 = Payout.objects.create(merchant=self.merchant, bank_account=self.bank_account, amount_paise=300000, state=Payout.COMPLETED)
        finalize_payout(p1)
        
        # Make a failed payout (was processed, then failed -> release funds)
        from payouts.services import release_held_funds
        p2 = Payout.objects.create(merchant=self.merchant, bank_account=self.bank_account, amount_paise=100000, state=Payout.FAILED)
        release_held_funds(p2) # this writes a credit
        
        # Make a pending payout (no ledger entry, just hold)
        p3 = Payout.objects.create(merchant=self.merchant, bank_account=self.bank_account, amount_paise=400000, state=Payout.PENDING)
        
        # Refresh everything
        self.merchant.refresh_from_db()
        
        # Compute manually
        from django.db.models import Sum
        credits = LedgerEntry.objects.filter(merchant=self.merchant, entry_type=LedgerEntry.CREDIT).aggregate(Sum('amount_paise'))['amount_paise__sum'] or 0
        debits = LedgerEntry.objects.filter(merchant=self.merchant, entry_type=LedgerEntry.DEBIT).aggregate(Sum('amount_paise'))['amount_paise__sum'] or 0
        
        net_ledger = credits - debits
        computed_total = self.merchant.available_balance_paise + self.merchant.held_balance_paise
        
        self.assertEqual(net_ledger, computed_total)
