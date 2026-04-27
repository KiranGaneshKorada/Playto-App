import uuid
from django.db import models
from django.utils import timezone
from datetime import timedelta

class Payout(models.Model):
    PENDING = 'pending'
    PROCESSING = 'processing'
    COMPLETED = 'completed'
    FAILED = 'failed'
    
    STATE_CHOICES = (
        (PENDING, 'Pending'),
        (PROCESSING, 'Processing'),
        (COMPLETED, 'Completed'),
        (FAILED, 'Failed'),
    )

    LEGAL_TRANSITIONS = {
        'pending':    ['processing'],
        'processing': ['completed', 'failed'],
        'completed':  [],
        'failed':     [],
    }

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    merchant = models.ForeignKey(
        'merchants.Merchant', 
        on_delete=models.PROTECT, 
        related_name='payouts'
    )
    bank_account = models.ForeignKey(
        'merchants.BankAccount',
        on_delete=models.PROTECT
    )
    amount_paise = models.BigIntegerField()
    state = models.CharField(max_length=20, choices=STATE_CHOICES, default=PENDING)
    attempts = models.PositiveIntegerField(default=0)
    max_attempts = models.PositiveIntegerField(default=3)
    failure_reason = models.TextField(blank=True)
    processing_started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.CheckConstraint(
                check=models.Q(amount_paise__gt=0),
                name='payout_amount_must_be_positive'
            )
        ]

    def transition(self, new_state):
        if new_state not in self.LEGAL_TRANSITIONS.get(self.state, []):
            raise ValueError(f"Illegal transition from {self.state} to {new_state}")
        
        self.state = new_state
        if new_state == self.PROCESSING:
            self.processing_started_at = timezone.now()
        elif new_state in [self.COMPLETED, self.FAILED]:
            self.completed_at = timezone.now()
            
        self.save()

    @property
    def is_stuck(self) -> bool:
        if self.state == self.PROCESSING and self.processing_started_at:
            return self.processing_started_at < timezone.now() - timedelta(seconds=30)
        return False

    @property
    def can_retry(self) -> bool:
        return self.attempts < self.max_attempts

    def __str__(self):
        return f"Payout {self.id} - {self.merchant} - {self.state}"


class IdempotencyKey(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    merchant = models.ForeignKey('merchants.Merchant', on_delete=models.CASCADE)
    key = models.CharField(max_length=255)
    payout = models.OneToOneField(Payout, on_delete=models.CASCADE, null=True, blank=True)
    response_body = models.JSONField(null=True, blank=True)
    response_status = models.PositiveIntegerField(null=True, blank=True)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['merchant', 'key'], name='unique_idempotency_key_per_merchant')
        ]

    @classmethod
    def get_valid(cls, merchant, key):
        try:
            idempotency_key = cls.objects.get(merchant=merchant, key=key)
            if idempotency_key.expires_at > timezone.now():
                return idempotency_key
            return None
        except cls.DoesNotExist:
            return None

    def __str__(self):
        return f"{self.key} for {self.merchant}"
