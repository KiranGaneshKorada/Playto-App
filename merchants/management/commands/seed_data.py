import random
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction
from merchants.models import Merchant, BankAccount
from ledger.models import LedgerEntry
from payouts.models import Payout

class Command(BaseCommand):
    help = 'Seeds initial realistic data'

    def handle(self, *args, **options):
        self.stdout.write("Seeding realistic data...")

        merchants_data = [
            {
                "name": "Arjun Sharma",
                "email": "arjun@designstudio.in",
                "phone": "+91-9876543210",
                "credits": [25000, 30000, 15000, 15000]
            },
            {
                "name": "Priya Nair",
                "email": "priya@codewithnair.dev",
                "phone": "+91-9123456789",
                "credits": [40000, 50000, 30000]
            },
            {
                "name": "Ravi Mehta",
                "email": "ravi@techfreelancer.io",
                "phone": "+91-9988776655",
                "credits": [10000, 8000, 12000, 9000, 6000]
            }
        ]

        merchants_created_count = 0
        bank_accounts_created_count = 0
        ledger_entries_created_count = 0

        now = timezone.now()

        with transaction.atomic():
            for m_data in merchants_data:
                # Create User
                from django.contrib.auth.models import User
                user, _ = User.objects.get_or_create(
                    username=m_data['email'],
                    email=m_data['email']
                )
                user.set_password('password123')
                user.save()

                merchant, m_created = Merchant.objects.get_or_create(
                    email=m_data['email'],
                    defaults={
                        'name': m_data['name'],
                        'phone': m_data['phone'],
                        'user': user
                    }
                )
                if not m_created and not merchant.user:
                    merchant.user = user
                    merchant.save(update_fields=['user'])
                if m_created:
                    merchants_created_count += 1

                # Primary HDFC
                _, b1_created = BankAccount.objects.get_or_create(
                    merchant=merchant,
                    account_number="123456789012",
                    bank_name="HDFC Bank",
                    defaults={
                        'account_holder_name': m_data['name'],
                        'ifsc_code': 'HDFC0001234',
                        'is_primary': True
                    }
                )
                if b1_created:
                    bank_accounts_created_count += 1

                # Secondary ICICI
                _, b2_created = BankAccount.objects.get_or_create(
                    merchant=merchant,
                    account_number="098765432109",
                    bank_name="ICICI Bank",
                    defaults={
                        'account_holder_name': m_data['name'],
                        'ifsc_code': 'ICIC0005678',
                        'is_primary': False
                    }
                )
                if b2_created:
                    bank_accounts_created_count += 1

                # Ledger Credits
                for i, amount_rupees in enumerate(m_data['credits']):
                    amount_paise = amount_rupees * 100
                    desc = f"Customer payment received - Invoice #INV-{merchant.name[:3].upper()}-{i+1}"
                    
                    # Idempotent check
                    if not LedgerEntry.objects.filter(merchant=merchant, description=desc, entry_type=LedgerEntry.CREDIT).exists():
                        entry = LedgerEntry.record_credit(
                            merchant=merchant,
                            amount_paise=amount_paise,
                            description=desc
                        )
                        # Backdate
                        entry.created_at = now - timedelta(days=random.randint(1, 30))
                        entry.save(update_fields=['created_at'])
                        ledger_entries_created_count += 1

            # Payouts for Arjun
            arjun = Merchant.objects.get(email="arjun@designstudio.in")
            arjun_primary_bank = BankAccount.objects.get(merchant=arjun, is_primary=True)
            
            payouts_to_create = [20000, 10000]
            
            for i, p_amount in enumerate(payouts_to_create):
                p_amount_paise = p_amount * 100
                desc = f"Withdrawal request seed {i+1}"
                if not Payout.objects.filter(merchant=arjun, amount_paise=p_amount_paise, state=Payout.COMPLETED).count() > i:
                    payout = Payout.objects.create(
                        merchant=arjun,
                        bank_account=arjun_primary_bank,
                        amount_paise=p_amount_paise,
                        state=Payout.COMPLETED,
                        processing_started_at=now - timedelta(days=5),
                        completed_at=now - timedelta(days=4)
                    )
                    
                    # Backdate payout
                    payout.created_at = now - timedelta(days=5)
                    payout.save(update_fields=['created_at'])

                    entry = LedgerEntry.record_debit(
                        merchant=arjun,
                        amount_paise=p_amount_paise,
                        description=f"Withdrawal request {payout.id}",
                        reference_id=payout.id
                    )
                    # Backdate ledger entry to match payout creation
                    entry.created_at = payout.created_at
                    entry.save(update_fields=['created_at'])
                    
                    ledger_entries_created_count += 1

        self.stdout.write(self.style.SUCCESS(f"  ✓ Created {merchants_created_count} merchants"))
        self.stdout.write(self.style.SUCCESS(f"  ✓ Created {bank_accounts_created_count} bank accounts"))
        self.stdout.write(self.style.SUCCESS(f"  ✓ Created {ledger_entries_created_count} ledger entries"))
        self.stdout.write("\n  Merchant balances:")
        
        for m in Merchant.objects.all():
            available_rupees = m.available_balance_paise / 100
            self.stdout.write(f"    {m.name}:  ₹{available_rupees:,.0f} available")
