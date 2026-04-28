from django.urls import path
from django.http import HttpResponseNotAllowed
from django.views.decorators.csrf import csrf_exempt
from payouts.views import (
    BalanceView,
    BankAccountListView,
    PayoutCreateView,
    PayoutListView,
    PayoutDetailView,
    LedgerView
)

@csrf_exempt
def payouts_dispatcher(request, *args, **kwargs):
    if request.method == 'GET':
        return PayoutListView.as_view()(request, *args, **kwargs)
    elif request.method == 'POST':
        return PayoutCreateView.as_view()(request, *args, **kwargs)
    return HttpResponseNotAllowed(['GET', 'POST'])

urlpatterns = [
    path('v1/balance/', BalanceView.as_view(), name='v1-balance'),
    path('v1/bank-accounts/', BankAccountListView.as_view(), name='v1-bank-accounts'),
    path('v1/payouts/', payouts_dispatcher, name='v1-payouts'),
    path('v1/payouts/<uuid:payout_id>/', PayoutDetailView.as_view(), name='v1-payout-detail'),
    path('v1/ledger/', LedgerView.as_view(), name='v1-ledger'),
]
