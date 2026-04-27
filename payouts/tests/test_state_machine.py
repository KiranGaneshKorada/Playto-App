from django.test import TestCase
from payouts.models import Payout
from ledger.models import LedgerEntry
from payouts.tests.factories import MerchantFactory, BankAccountFactory, PayoutFactory, LedgerEntryFactory

class StateMachineTests(TestCase):
    def setUp(self):
        self.merchant = MerchantFactory()
        self.bank_account = BankAccountFactory(merchant=self.merchant)
        # Setup: Merchant with ₹10,000 balance
        LedgerEntryFactory(merchant=self.merchant, amount_paise=1000000)

    def test_legal_transitions_succeed(self):
        # pending -> processing
        payout = PayoutFactory(merchant=self.merchant, bank_account=self.bank_account, state=Payout.PENDING)
        payout.transition(Payout.PROCESSING)
        self.assertEqual(payout.state, Payout.PROCESSING)
        self.assertIsNotNone(payout.processing_started_at)
        
        # processing -> completed
        payout.transition(Payout.COMPLETED)
        self.assertEqual(payout.state, Payout.COMPLETED)
        self.assertIsNotNone(payout.completed_at)

        # processing -> failed
        payout2 = PayoutFactory(merchant=self.merchant, bank_account=self.bank_account, state=Payout.PENDING)
        payout2.transition(Payout.PROCESSING)
        payout2.transition(Payout.FAILED)
        self.assertEqual(payout2.state, Payout.FAILED)
        self.assertIsNotNone(payout2.completed_at)

    def test_illegal_transitions_raise_error(self):
        # completed -> *
        p_completed = PayoutFactory(merchant=self.merchant, bank_account=self.bank_account, state=Payout.COMPLETED)
        with self.assertRaises(ValueError):
            p_completed.transition(Payout.PENDING)
        with self.assertRaises(ValueError):
            p_completed.transition(Payout.PROCESSING)
        with self.assertRaises(ValueError):
            p_completed.transition(Payout.FAILED)
            
        # failed -> *
        p_failed = PayoutFactory(merchant=self.merchant, bank_account=self.bank_account, state=Payout.FAILED)
        with self.assertRaises(ValueError):
            p_failed.transition(Payout.PENDING)
        with self.assertRaises(ValueError):
            p_failed.transition(Payout.PROCESSING)
        with self.assertRaises(ValueError):
            p_failed.transition(Payout.COMPLETED)

        # pending -> completed
        p_pending = PayoutFactory(merchant=self.merchant, bank_account=self.bank_account, state=Payout.PENDING)
        with self.assertRaises(ValueError):
            p_pending.transition(Payout.COMPLETED)

    def test_failed_payout_refunds_funds_atomically(self):
        # Create pending payout for ₹6,000 (funds held)
        payout = PayoutFactory(merchant=self.merchant, bank_account=self.bank_account, amount_paise=600000, state=Payout.PENDING)
        
        # Assert available is ₹4,000 before failure
        self.assertEqual(self.merchant.available_balance_paise, 400000)
        
        # Action: Simulate payout failure
        from payouts.services import release_held_funds
        from django.db import transaction
        
        with transaction.atomic():
            release_held_funds(payout)
            payout.transition(Payout.PROCESSING)
            payout.transition(Payout.FAILED)
            
        # Assert: Merchant available balance returns to ₹10,000.
        self.merchant.refresh_from_db()
        self.assertEqual(self.merchant.available_balance_paise, 1000000)
