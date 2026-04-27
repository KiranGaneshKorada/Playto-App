import uuid
from django.db import models
from django.db.models import Sum, Q

class LedgerEntryManager(models.Manager):
    def balance_for(self, merchant):
        result = self.filter(merchant=merchant).aggregate(
            credits=Sum('amount_paise', filter=Q(entry_type=LedgerEntry.CREDIT)),
            debits=Sum('amount_paise', filter=Q(entry_type=LedgerEntry.DEBIT))
        )
        credits = result['credits'] or 0
        debits = result['debits'] or 0
        return {
            'credits': credits,
            'debits': debits,
            'net': credits - debits
        }

class LedgerEntry(models.Model):
    CREDIT = 'credit'
    DEBIT = 'debit'
    ENTRY_TYPE_CHOICES = (
        (CREDIT, 'Credit'),
        (DEBIT, 'Debit'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    merchant = models.ForeignKey(
        'merchants.Merchant', 
        on_delete=models.PROTECT, 
        related_name='ledger_entries'
    )
    entry_type = models.CharField(max_length=10, choices=ENTRY_TYPE_CHOICES)
    amount_paise = models.BigIntegerField()
    reference_id = models.UUIDField(null=True, blank=True)
    description = models.CharField(max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = LedgerEntryManager()

    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.CheckConstraint(
                check=models.Q(amount_paise__gt=0),
                name='ledger_amount_must_be_positive'
            )
        ]

    @classmethod
    def record_credit(cls, merchant, amount_paise, description, reference_id=None):
        return cls.objects.create(
            merchant=merchant,
            entry_type=cls.CREDIT,
            amount_paise=amount_paise,
            description=description,
            reference_id=reference_id
        )

    @classmethod
    def record_debit(cls, merchant, amount_paise, description, reference_id=None):
        return cls.objects.create(
            merchant=merchant,
            entry_type=cls.DEBIT,
            amount_paise=amount_paise,
            description=description,
            reference_id=reference_id
        )

    def __str__(self):
        return f"{self.entry_type} {self.amount_paise} for {self.merchant}"
