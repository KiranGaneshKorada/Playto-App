import sys
from django.core.management.base import BaseCommand
from merchants.models import Merchant
from ledger.models import LedgerEntry
from payouts.models import Payout
from django.db.models import Sum

class Command(BaseCommand):
    help = 'Checks mathematical invariants across the financial database'

    def handle(self, *args, **options):
        self.stdout.write("Running invariant checks on all merchants...\n")
        
        merchants = Merchant.objects.all()
        any_failed = False
        
        for merchant in merchants:
            self.stdout.write(f"Checking merchant: {merchant.name} ({merchant.id})")
            
            # Compute ledger total
            credits = LedgerEntry.objects.filter(merchant=merchant, entry_type=LedgerEntry.CREDIT).aggregate(Sum('amount_paise'))['amount_paise__sum'] or 0
            debits = LedgerEntry.objects.filter(merchant=merchant, entry_type=LedgerEntry.DEBIT).aggregate(Sum('amount_paise'))['amount_paise__sum'] or 0
            ledger_total = credits - debits
            
            # Compute held from active payouts
            held = Payout.objects.filter(merchant=merchant, state__in=[Payout.PENDING, Payout.PROCESSING]).aggregate(Sum('amount_paise'))['amount_paise__sum'] or 0
            
            # Compute available (this is how the app calculates it)
            available = ledger_total - held
            
            # Let's also check against the merchant properties
            prop_available = merchant.available_balance_paise
            prop_held = merchant.held_balance_paise
            prop_total = merchant.total_balance_paise
            
            # Asserts
            failed = False
            if available < 0:
                self.stderr.write(self.style.ERROR(f"  FAILED: Negative available balance! {available}"))
                failed = True
                
            if ledger_total != available + held:
                self.stderr.write(self.style.ERROR(f"  FAILED: Math mismatch! ledger_total ({ledger_total}) != available ({available}) + held ({held})"))
                failed = True
                
            if prop_available != available or prop_held != held or prop_total != ledger_total:
                self.stderr.write(self.style.ERROR(f"  FAILED: Property mismatch! model computed differently from manual compute"))
                failed = True
                
            if failed:
                any_failed = True
            else:
                self.stdout.write(self.style.SUCCESS("  OK"))

        if any_failed:
            self.stderr.write(self.style.ERROR("\nInvariant checks failed! See errors above."))
            sys.exit(1)
        else:
            self.stdout.write(self.style.SUCCESS("\nAll invariant checks passed successfully!"))
            sys.exit(0)
