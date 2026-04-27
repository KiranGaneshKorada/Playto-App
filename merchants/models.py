import uuid
from django.db import models
from django.db.models import Q, Sum

from django.conf import settings

class Merchant(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    name = models.CharField(max_length=200)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    @property
    def total_balance_paise(self):
        from ledger.models import LedgerEntry
        return LedgerEntry.objects.balance_for(self)['net']

    @property
    def held_balance_paise(self):
        from payouts.models import Payout
        held = Payout.objects.filter(
            merchant=self, 
            state__in=[Payout.PENDING, Payout.PROCESSING]
        ).aggregate(Sum('amount_paise'))['amount_paise__sum'] or 0
        return held

    @property
    def available_balance_paise(self):
        return self.total_balance_paise - self.held_balance_paise

    def __str__(self):
        return f"{self.name} ({self.email})"

class BankAccount(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    merchant = models.ForeignKey(Merchant, on_delete=models.CASCADE, related_name='bank_accounts')
    account_holder_name = models.CharField(max_length=200)
    account_number = models.CharField(max_length=20)
    ifsc_code = models.CharField(max_length=11)
    bank_name = models.CharField(max_length=200)
    is_primary = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['merchant'],
                condition=Q(is_primary=True),
                name='unique_primary_bank_account'
            )
        ]

    def __str__(self):
        return f"{self.bank_name} ending in {self.account_number[-4:]}"
