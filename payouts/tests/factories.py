import factory
from merchants.models import Merchant, BankAccount
from ledger.models import LedgerEntry
from payouts.models import Payout
from django.contrib.auth import get_user_model

User = get_user_model()

class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User
    
    username = factory.Sequence(lambda n: f"user_{n}")
    email = factory.Sequence(lambda n: f"user_{n}@example.com")


class MerchantFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Merchant

    user = factory.SubFactory(UserFactory)
    name = factory.Faker('company')
    email = factory.Sequence(lambda n: f"merchant_{n}@example.com")
    phone = factory.Sequence(lambda n: f"+9198765432{n:02d}")


class BankAccountFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = BankAccount

    merchant = factory.SubFactory(MerchantFactory)
    account_holder_name = factory.Faker('name')
    account_number = factory.Sequence(lambda n: f"000000{n}")
    ifsc_code = "HDFC0001234"
    bank_name = "HDFC Bank"
    is_primary = True


class LedgerEntryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = LedgerEntry

    merchant = factory.SubFactory(MerchantFactory)
    entry_type = LedgerEntry.CREDIT
    amount_paise = 1000000 # 10,000 INR
    description = "Test credit"


class PayoutFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Payout

    merchant = factory.SubFactory(MerchantFactory)
    bank_account = factory.SubFactory(BankAccountFactory)
    amount_paise = 500000
    state = Payout.PENDING
