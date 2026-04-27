import uuid
from datetime import timedelta
from django.utils import timezone
from rest_framework.test import APITestCase
from rest_framework import status
from payouts.models import Payout, IdempotencyKey
from payouts.tests.factories import MerchantFactory, BankAccountFactory, LedgerEntryFactory

class IdempotencyTests(APITestCase):
    def setUp(self):
        self.merchant = MerchantFactory()
        self.bank_account = BankAccountFactory(merchant=self.merchant)
        LedgerEntryFactory(merchant=self.merchant, amount_paise=1000000) # Give funds
        self.client.force_authenticate(user=self.merchant.user)
        self.url = '/api/v1/payouts'

    def test_same_key_returns_same_response(self):
        idempotency_key = str(uuid.uuid4())
        payload = {
            'amount_paise': 100000,
            'bank_account_id': str(self.bank_account.id)
        }

        # First request
        response1 = self.client.post(self.url, payload, format='json', HTTP_IDEMPOTENCY_KEY=idempotency_key)
        self.assertEqual(response1.status_code, status.HTTP_201_CREATED)

        # Exact same request again
        response2 = self.client.post(self.url, payload, format='json', HTTP_IDEMPOTENCY_KEY=idempotency_key)
        
        # Assert: Both responses are identical
        self.assertEqual(response2.status_code, status.HTTP_201_CREATED) # Returns 201 as cached
        self.assertEqual(response1.data, response2.data)
        
        # Assert: Only ONE Payout object exists
        self.assertEqual(Payout.objects.count(), 1)
        
        # Assert: Second response has header X-Idempotent-Replayed: true
        self.assertEqual(response2.headers.get('X-Idempotent-Replayed'), 'true')

    def test_different_keys_create_different_payouts(self):
        payload = {
            'amount_paise': 100000,
            'bank_account_id': str(self.bank_account.id)
        }

        # First request
        self.client.post(self.url, payload, format='json', HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()))
        
        # Second request with different key
        self.client.post(self.url, payload, format='json', HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()))
        
        # Assert: Two separate Payout objects created
        self.assertEqual(Payout.objects.count(), 2)

    def test_expired_key_creates_new_payout(self):
        idempotency_key = str(uuid.uuid4())
        
        # Manually create an expired key
        ik = IdempotencyKey.objects.create(
            merchant=self.merchant,
            key=idempotency_key,
            expires_at=timezone.now() - timedelta(hours=1)
        )

        payload = {
            'amount_paise': 100000,
            'bank_account_id': str(self.bank_account.id)
        }

        # Send a request with the same key string
        response = self.client.post(self.url, payload, format='json', HTTP_IDEMPOTENCY_KEY=idempotency_key)
        
        # Assert: A NEW payout is created (since the view uses IdempotencyKey.get_valid which checks expiry)
        # Wait, if get_valid returns None, it tries to create. But there is a UniqueConstraint on (merchant, key).
        # Ah, the instructions say "expired keys are treated as new", but if there's a UniqueConstraint,
        # it will raise IntegrityError if we try to insert the same key again!
        # The prompt says: "Assert: A NEW payout is created (expired keys are treated as new)".
        # In `services.py` I create the key `IdempotencyKey.objects.create(merchant, key)`. This will fail
        # with IntegrityError if the key already exists (expired or not) because of the DB constraint!
        # Let me just write the test as requested. If it fails, I'll need to update services.py or models.py.
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Payout.objects.count(), 1)
