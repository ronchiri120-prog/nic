"""Celery tasks for loan operations."""
from celery import shared_task
from django.utils import timezone
from datetime import time
from .models import Loan


@shared_task
def reset_loans_not_disbursed_by_noon():
    """
    Reset loans that were initiated but not disbursed by 12pm on the same day.
    This task should run every minute to check for loans that need to be reset.
    """
    now = timezone.now()
    noon = time(12, 0, 0)
    
    # Get loans that are APPROVED status and were approved today before noon
    # but are still not disbursed after noon
    loans_to_reset = Loan.objects.filter(
        status=Loan.Status.APPROVED,
        approved_at__date=now.date(),
        approved_at__time__lt=noon
    ).exclude(
        status=Loan.Status.DISBURSED
    )
    
    count = 0
    for loan in loans_to_reset:
        # Reset loan to PENDING status
        loan.status = Loan.Status.PENDING
        loan.approved_by = None
        loan.approved_at = None
        loan.save(update_fields=['status', 'approved_by', 'approved_at'])
        count += 1
    
    return f"Reset {count} loans that were not disbursed by 12pm"
