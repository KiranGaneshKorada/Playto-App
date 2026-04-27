# EXPLAINER

**Jump straight to the answers:**

[ 1. The Ledger ](#1-the-ledger)  ·  [ 2. The Lock ](#2-the-lock)  ·  [ 3. The Idempotency ](#3-the-idempotency--created-a-model-with-key-merchant-to-store-the-response)  ·  [ 4. The State Machine ](#4-the-state-machine)  ·  [ 5. The AI Audit ](#5-the-ai-audit)  ·  [ docker-compose ](#bonus-docker-composeyml-for-postgres-and-reddis)  ·  [ How to verify ](#how-to-verify-the-claims-above)

The next three sections are setup (folder layout, models, request flows). 

---

## Folder Structure

```
playto-payout/
├── playto/        Django project config (settings, urls, celery)
├── merchants/     Merchant + BankAccount models. The "who is this".
├── ledger/        Append-only credits and debits. The single source of money truth.
├── payouts/       Payout state machine, idempotency, Celery tasks. The engine.
├── api/           Auth views (login, logout, me) and URL routing for v1.
├── frontend/      React + Vite + Tailwind dashboard.
├── manage.py
├── requirements.txt
├── docker-compose.yml   (Postgres + Redis only)
└── Makefile             (install, migrate, seed, worker, beat, dev)
```

---

## Models

**Merchant** — the user/business sending money.
- `id` — unique merchant ID
- `user` — linked Django user (for login)
- `name` — display name
- `email` — unique
- `phone` — contact number
- `is_active` — disabled flag
- `created_at`, `updated_at` — timestamps

**BankAccount** — where money goes. Only one primary per merchant.
- `id` — unique bank account ID
- `merchant` — owning merchant
- `account_holder_name` — name on the account
- `account_number` — bank account number
- `ifsc_code` — IFSC code
- `bank_name` — name of the bank
- `is_primary` — primary destination flag
- `is_active` — disabled flag
- `created_at` — created timestamp

**LedgerEntry** — one credit or debit row. Append-only.
- `id` — unique entry ID
- `merchant` — which merchant this entry is for
- `entry_type` — credit or debit
- `amount_paise` — always positive (sign lives in `entry_type`)
- `reference_id` — links a debit back to its payout
- `description` — what this entry is for
- `created_at` — when written

**Payout** — a withdrawal request. The state machine lives here.
- `id` — unique payout ID
- `merchant` — who is withdrawing
- `bank_account` — where the money goes
- `amount_paise` — withdrawal amount
- `state` — pending / processing / completed / failed
- `attempts` — current retry count
- `max_attempts` — retry cap (default 3)
- `failure_reason` — text reason if failed
- `processing_started_at` — when worker picked it up
- `completed_at` — when finished
- `created_at`, `updated_at` — timestamps

**IdempotencyKey** — caches the response for a (merchant, key) pair so retries replay the same body.
- `id` — unique row ID
- `merchant` — owning merchant
- `key` — the UUID sent by the client
- `payout` — payout linked to this key
- `response_body` — cached JSON response
- `response_status` — cached HTTP status
- `expires_at` — 24-hour expiry
- `created_at` — when written


---

## Request Flows


**`GET /api/v1/balance/`**

1. `api/urls.py` → `path('v1/balance/', BalanceView.as_view())`
2. `payouts/views.py::BalanceView.get` — reads `request.user.merchant`, hands it to the serializer.
3. `payouts/serializers.py::MerchantBalanceSerializer` — reads `available_balance_paise`, `held_balance_paise`, `total_balance_paise`. These are `@property` methods on `Merchant` that aggregate the ledger (`SUM(credits) - SUM(debits)`) and the pending/processing payouts. Returns paise as integers and INR as formatted strings.

---

**`GET /api/v1/bank-accounts/`**

1. `api/urls.py` → `path('v1/bank-accounts/', BankAccountListView.as_view())`
2. `payouts/views.py::BankAccountListView.get` — `BankAccount.objects.filter(merchant=merchant, is_active=True)`.
3. `payouts/serializers.py::BankAccountSerializer` — masks `account_number` so only the last 4 digits leave the server.

---

**`GET /api/v1/payouts/`**

1. `api/urls.py` → `path('v1/payouts/', payouts_dispatcher)`. The dispatcher is a tiny function that routes GET to `PayoutListView` and POST to `PayoutCreateView` (Django's `path` can't split by method on its own).
2. `payouts/views.py::PayoutListView.get` — filters by merchant, applies optional `?state=` and `?limit=` (default 20), orders by `-created_at`.
3. `payouts/serializers.py::PayoutSerializer` — nests `BankAccountSerializer` for the destination, formats `amount_inr`, includes `state_display`.

---

**`GET /api/v1/ledger/`**

1. `api/urls.py` → `path('v1/ledger/', LedgerView.as_view())`
2. `payouts/views.py::LedgerView.get` — `LedgerEntry.objects.filter(merchant=merchant).order_by('-created_at')[:50]`.
3. `payouts/serializers.py::LedgerEntrySerializer` — returns `entry_type`, `amount_paise`, `amount_inr`, `description`, `reference_id`, `created_at`.

---

### The main payout call: `POST /api/v1/payouts/`

This is the only path that moves money.

1. **Frontend** — `useCreatePayout` hook reads the idempotency key from `useState` and sends:
   ```
   POST /api/v1/payouts/
     headers: Idempotency-Key: <uuid>, X-CSRFToken: <token>
     body:    { amount_paise, bank_account_id }
   ```

2. `api/urls.py` → `payouts_dispatcher` → POST routes to `PayoutCreateView`.

3. `payouts/views.py::PayoutCreateView.post` does:
   - `request.META['HTTP_IDEMPOTENCY_KEY']` must be present and a valid UUID, else 400.
   - Runs `PayoutCreateSerializer(data=request.data, context={'merchant': merchant})`.
   - Calls `services.create_payout(...)`.
   - On `InsufficientFundsError` → returns 422 with available + requested paise.
   - Otherwise returns 201 with the response body. Adds `X-Idempotent-Replayed: true` header if the result was a cached replay.

4. `payouts/serializers.py::PayoutCreateSerializer` validates input:
   - `amount_paise` must be between 100 (₹1) and 1,000,000,000 (₹1 crore).
   - `bank_account_id` is checked to belong to this merchant and to be active.

5. `payouts/services.py::create_payout` does the transactional work:
   ```
   BEGIN TRANSACTION
     LOCK merchant row (SELECT FOR UPDATE)
     Lookup IdempotencyKey (merchant, key)
       → if hit: return cached response, replayed=true
     hold_funds(merchant, amount):
       Lock ledger rows (SELECT FOR UPDATE)
       Compute available − held
         → if not enough: raise InsufficientFundsError
     INSERT Payout(state=pending)
     UPSERT IdempotencyKey with cached response_body + status
   COMMIT

   Enqueue Celery task: process_payout.delay(payout.id)
   Return (payout, response_body, 201, replayed=false)
   ```

6. View serializes the new payout via `PayoutSerializer` and sends 201 back to the client.

7. **Frontend** — `useCreatePayout.onSuccess`:
   - Invalidates `['balance']` and `['payouts']` queries → both refetch automatically.
   - If the response was NOT a replay, generates a new idempotency key for the next submission. If it WAS a replay, keeps the same key.

---

### Async path (after the 201 response)

**Celery worker** (`payouts/tasks.py::process_payout`)
- Locks the payout row with `SELECT FOR UPDATE SKIP LOCKED` so two workers can't pick up the same row.
- Transitions pending → processing.
- Simulates a bank API: 70% success, 20% fail, 10% stuck.
  - Success → writes a DEBIT `LedgerEntry`, transitions → completed.
  - Fail → transitions → failed (held funds auto-released since state is no longer pending/processing).
  - Stuck → leaves the row in processing for the reaper to handle.

**Celery Beat** (`payouts/tasks.py::reap_stuck_payouts`, every 15 seconds)
- Finds payouts stuck in processing for more than 30 seconds.
- If `attempts < max_attempts`: resets to pending and re-enqueues with exponential backoff (`2^attempts × 5` seconds).
- Else: transitions to failed with "exceeded max attempts".

---


## 1. The Ledger

I don't store a balance number anywhere. The balance is calculated from a list of credit and debit entries.

```python
# ledger/models.py
class LedgerEntryManager(models.Manager):
    def balance_for(self, merchant):
        result = self.filter(merchant=merchant).aggregate(
            credits=Sum('amount_paise', filter=Q(entry_type=LedgerEntry.CREDIT)),
            debits=Sum('amount_paise', filter=Q(entry_type=LedgerEntry.DEBIT))
        )
        credits = result['credits'] or 0
        debits = result['debits'] or 0
        return {'credits': credits, 'debits': debits, 'net': credits - debits}
```



Why I did it this way:
- **Paise (integer), not rupees (float).** I use `BigIntegerField` everywhere. Floats lose precision (`0.1 + 0.2 != 0.3`) and you really don't want that in a money system.
- **No balance column means no race.** Two requests can't both run `UPDATE merchant SET balance = balance - X` and lose a write, because there's no row to fight over.


---

## 2. The Lock

```python
# payouts/services.py - hold_funds()
def hold_funds(merchant, amount_paise):
    with transaction.atomic():
        list(LedgerEntry.objects.select_for_update()
                                .filter(merchant=merchant)
                                .values('id'))

        balance = LedgerEntry.objects.balance_for(merchant)['net']
        held = Payout.objects.filter(
            merchant=merchant,
            state__in=[Payout.PENDING, Payout.PROCESSING]
        ).aggregate(Sum('amount_paise'))['amount_paise__sum'] or 0

        if balance - held < amount_paise:
            raise InsufficientFundsError(available=balance - held,
                                         requested=amount_paise)
```



**The thing that makes this work: `SELECT ... FOR UPDATE` row-level locking in Postgres.**

When request A enters the transaction and locks the merchant row + the merchant's ledger rows, request B waits at its own `SELECT ... FOR UPDATE` until A commits. By the time B reads the balance, A's pending payout is already in the database, so B's `held` includes A's hold and B fails with `InsufficientFundsError`.

---

## 3. The Idempotency ( Created a model with key-merchant to store the response)

Every `POST /api/v1/payouts/` needs an `Idempotency-Key` header (must be a UUID). Here's what `create_payout` does in pseudocode:

```
function create_payout(merchant, amount, bank, key):
    BEGIN TRANSACTION
        LOCK merchant row                       # SELECT FOR UPDATE

        # 1. Have we seen this key before? (checked INSIDE the lock)
        cached = lookup IdempotencyKey where (merchant, key) and not expired
        if cached:
            return cached.response_body, status=201, replayed=true

        # 2. Otherwise do the work
        check_balance_and_hold(merchant, amount)
        payout = INSERT Payout(state=pending)
        ik     = UPSERT IdempotencyKey(merchant, key,
                                       payout=payout,
                                       expires_at=now+24h)
        ik.response_body   = serialize(payout)
        ik.response_status = 201
    COMMIT

    enqueue Celery task(payout.id)
    return ik.response_body, status=201, replayed=false
```


**What if request B arrives while A is still running?**

```
A: BEGIN, lock merchant
A:   lookup key → miss
A:   INSERT IdempotencyKey (with response_body)
                                B: BEGIN, lock merchant → BLOCKS on A
A: COMMIT → lock released
                                B:   unblocks, lock acquired
                                B:   lookup key → HIT (sees A's row)
                                B:   return cached response, replayed=true
```

The check sits inside the lock. So by the time B holds the merchant lock, A has either finished (and B sees A's row) or never existed. There's no way for B to miss A's row and then go on to create a duplicate. One key, one Payout. Always.

---

## 4. The State Machine

A completed payout can't become anything else. The check lives in the model, not spread across views.

```python
# payouts/models.py
class Payout(models.Model):
    LEGAL_TRANSITIONS = {
        'pending':    ['processing'],
        'processing': ['completed', 'failed'],
        'completed':  [],          # terminal
        'failed':     [],          # terminal
    }

    def transition(self, new_state):
        if new_state not in self.LEGAL_TRANSITIONS.get(self.state, []):
            raise ValueError(f"Illegal transition from {self.state} to {new_state}")

        self.state = new_state
        if new_state == self.PROCESSING:
            self.processing_started_at = timezone.now()
        elif new_state in [self.COMPLETED, self.FAILED]:
            self.completed_at = timezone.now()
        self.save()
```

`failed → completed`, `completed → failed`, `completed → pending`, `pending → completed` (skipping processing). All of these raise `ValueError`. `payouts/tests/test_state_machine.py::test_illegal_transitions_raise_error` checks every illegal path.



---

## 5. The AI Audit

I used Claude and Antigravity as a pair programmer. Most of what it gave me was fine. One thing was subtly wrong in a way that would only show up under load.

**What it gave me** for `hold_funds`:

```python
def hold_funds(merchant, amount_paise):
    with transaction.atomic():
        LedgerEntry.objects.select_for_update().filter(merchant=merchant)

        balance = LedgerEntry.objects.balance_for(merchant)['net']
        held = Payout.objects.filter(
            merchant=merchant,
            state__in=[Payout.PENDING, Payout.PROCESSING]
        ).aggregate(Sum('amount_paise'))['amount_paise__sum'] or 0

        if balance - held < amount_paise:
            raise InsufficientFundsError(...)
```

**What I caught.** This looks right. It compiles. It runs. It even passes the single-threaded happy path. But the first line is silently broken.

`LedgerEntry.objects.select_for_update().filter(merchant=merchant)` is a lazy queryset in Django. The SQL doesn't actually run until you iterate it, slice it, call `len()` on it, or otherwise consume it. The line as written builds a queryset object, throws it away, and **acquires no lock at all**. The next line then runs an aggregate that issues its own un-locked SELECT, and the whole "lock" is theatre.


**What I changed it to:**

```python
list(LedgerEntry.objects.select_for_update()
                        .filter(merchant=merchant)
                        .values('id'))
```


---

## Bonus: docker-compose.yml (for Postgres and Reddis)

```yaml
services:
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: playto
    ports: ["5432:5432"]
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    ports: ["6380:6379"]   # 6380 host, 6379 container — avoids clashing with a local Redis

volumes:
  postgres_data:
```



---

## How to verify the claims above

```bash
python manage.py migrate
python manage.py seed_data
python manage.py check_invariants     # asserts available + held == ledger_total for every merchant
python manage.py test payouts.tests   # state machine, idempotency, real-thread concurrency
```
