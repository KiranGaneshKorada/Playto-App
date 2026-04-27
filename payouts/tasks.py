import time
import random
import logging
from datetime import timedelta
from django.db import transaction
from django.utils import timezone
from playto.celery import app
from .models import Payout
from .services import finalize_payout, release_held_funds

logger = logging.getLogger(__name__)

@app.task(bind=True, name='payouts.tasks.process_payout')
def process_payout(self, payout_id):
    """
    Process a payout simulating a bank API call.
    """
    # 1. Fetch payout with select_for_update(skip_locked=True)
    with transaction.atomic():
        try:
            # We use select_for_update(skip_locked=True) to avoid blocking or waiting
            # on another worker that might be processing this exact payout.
            # Using filter + first() is safer for skip_locked to avoid DoesNotExist exceptions,
            # but we can catch DoesNotExist.
            payout = Payout.objects.select_for_update(skip_locked=True).get(id=payout_id)
        except Payout.DoesNotExist:
            logger.warning(f"Payout {payout_id} not found or locked by another worker.")
            return

        if payout.state != Payout.PENDING:
            logger.info(f"Payout {payout_id} already processed (state: {payout.state})")
            return

        # 2. Inside transaction.atomic()
        payout.attempts += 1
        payout.transition(Payout.PROCESSING)
        payout.save()

    # 3. OUTSIDE the transaction, simulate bank API call
    r = random.random()
    if r < 0.70:
        outcome = 'success'
    elif r < 0.90:
        outcome = 'failed'
    else:
        outcome = 'stuck'

    if outcome == 'stuck':
        time.sleep(0.1)
        return

    if outcome == 'success':
        # 4. Handle success
        with transaction.atomic():
            try:
                payout = Payout.objects.select_for_update().get(id=payout_id)
            except Payout.DoesNotExist:
                return

            if payout.state != Payout.PROCESSING:
                return

            finalize_payout(payout)
            payout.transition(Payout.COMPLETED)
            payout.save()
            logger.info(f"Payout {payout_id} completed successfully")

    elif outcome == 'failed':
        # 5. Handle failure
        with transaction.atomic():
            try:
                payout = Payout.objects.select_for_update().get(id=payout_id)
            except Payout.DoesNotExist:
                return

            if payout.state != Payout.PROCESSING:
                return

            release_held_funds(payout)
            payout.failure_reason = 'Bank transfer failed'
            payout.transition(Payout.FAILED)
            payout.save()
            logger.info(f"Payout {payout_id} failed — funds returned to merchant")


@app.task(name='payouts.tasks.reap_stuck_payouts')
def reap_stuck_payouts():
    """
    Finds payouts stuck in processing for too long and retries or fails them.
    """
    # 1. Find all stuck payouts
    cutoff = timezone.now() - timedelta(seconds=30)
    
    # We evaluate the queryset inside the transaction loop using an explicit iterator or fetching IDs,
    # but the instruction implies doing select_for_update directly. 
    # Since select_for_update must be evaluated inside a transaction, we'll open a transaction 
    # for each stuck payout individually to avoid holding a giant lock, or select all locked in one block.
    # We will fetch IDs first, then process each in its own transaction.
    stuck_ids = list(Payout.objects.filter(
        state=Payout.PROCESSING,
        processing_started_at__lt=cutoff
    ).values_list('id', flat=True))

    checked_count = 0

    for pid in stuck_ids:
        with transaction.atomic():
            try:
                payout = Payout.objects.select_for_update(skip_locked=True).get(id=pid)
            except Payout.DoesNotExist:
                continue
                
            # Double check condition inside lock
            if payout.state != Payout.PROCESSING or payout.processing_started_at >= cutoff:
                continue
                
            checked_count += 1

            # 2a. Can retry
            if payout.can_retry:
                logger.info(f"Retrying stuck payout {payout.id}, attempt {payout.attempts}")
                
                # OVERRIDE state machine
                payout.state = Payout.PENDING
                payout.processing_started_at = None
                payout.save(update_fields=['state', 'processing_started_at', 'updated_at'])
                
                # Re-enqueue with exponential backoff
                countdown = (2 ** payout.attempts) * 5
                process_payout.apply_async(args=[str(payout.id)], countdown=countdown)
                
            # 2b. Exceeded max attempts
            else:
                logger.info(f"Payout {payout.id} exceeded max attempts — marking failed")
                release_held_funds(payout)
                payout.failure_reason = f'Exceeded max retry attempts ({payout.max_attempts})'
                payout.transition(Payout.FAILED)
                payout.save()

    # 3. Log summary
    logger.info(f"Reaper ran: checked {checked_count} payouts")
