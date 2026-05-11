"""
notifications/tasks.py
Celery async tasks for all notification and scheduled jobs.
"""
import logging
from celery import shared_task
from django.utils import timezone
from datetime import timedelta

logger = logging.getLogger('apps.notifications')


# ══════════════════════════════════════════════════════════════
#  SMS TASKS
# ══════════════════════════════════════════════════════════════

@shared_task(
    bind=True, name='notifications.send_sms',
    autoretry_for=(Exception,), retry_kwargs={'max_retries': 3, 'countdown': 30},
)
def task_send_sms(self, phone: str, message: str, sms_log_id: int = None,
                  customer_id: int = None, loan_id: int = None, template_key: str = 'CUSTOM'):
    """Async SMS sending — retries up to 3x on failure."""
    from apps.notifications.sms import send_sms, normalize_phone
    from apps.notifications.models import SMSLog

    # If we have a log entry, use it directly
    if sms_log_id:
        try:
            log = SMSLog.objects.get(id=sms_log_id)
            phone   = log.recipient
            message = log.message
        except SMSLog.DoesNotExist:
            pass

    result = send_sms(phone, message, template_key=template_key)
    logger.info(f'[TASK] SMS to {phone}: {result}')
    return result


@shared_task(name='notifications.sms_loan_disbursed')
def task_sms_loan_disbursed(loan_id: int):
    from apps.loans.models import Loan
    from apps.notifications.sms import sms_loan_disbursed
    try:
        loan = Loan.objects.select_related('customer', 'loan_officer').get(id=loan_id)
        result = sms_loan_disbursed(loan)
        logger.info(f'Disbursement SMS for {loan.loan_id}: {result}')
        return result
    except Loan.DoesNotExist:
        logger.error(f'Loan {loan_id} not found for SMS')


@shared_task(name='notifications.sms_payment_confirmed')
def task_sms_payment_confirmed(payment_id: int):
    from apps.payments.models import Payment
    from apps.notifications.sms import sms_payment_confirmed
    try:
        payment = Payment.objects.select_related('loan__customer').get(id=payment_id)
        return sms_payment_confirmed(payment)
    except Payment.DoesNotExist:
        logger.error(f'Payment {payment_id} not found for SMS')


@shared_task(name='notifications.sms_loan_approved')
def task_sms_loan_approved(loan_id: int):
    from apps.loans.models import Loan
    from apps.notifications.sms import sms_loan_approved
    try:
        loan = Loan.objects.select_related('customer').get(id=loan_id)
        return sms_loan_approved(loan)
    except Loan.DoesNotExist:
        pass


@shared_task(name='notifications.sms_loan_rejected')
def task_sms_loan_rejected(loan_id: int):
    from apps.loans.models import Loan
    from apps.notifications.sms import sms_loan_rejected
    try:
        loan = Loan.objects.select_related('customer').get(id=loan_id)
        return sms_loan_rejected(loan)
    except Loan.DoesNotExist:
        pass


# ══════════════════════════════════════════════════════════════
#  EMAIL TASKS
# ══════════════════════════════════════════════════════════════

@shared_task(name='notifications.email_loan_disbursed')
def task_email_loan_disbursed(loan_id: int):
    from apps.loans.models import Loan
    from apps.notifications.email_service import email_loan_disbursed
    try:
        loan = Loan.objects.select_related('customer', 'product').get(id=loan_id)
        return email_loan_disbursed(loan)
    except Loan.DoesNotExist:
        pass


@shared_task(name='notifications.email_loan_approved')
def task_email_loan_approved(loan_id: int):
    from apps.loans.models import Loan
    from apps.notifications.email_service import email_loan_approved
    try:
        loan = Loan.objects.select_related('customer').get(id=loan_id)
        return email_loan_approved(loan)
    except Loan.DoesNotExist:
        pass


@shared_task(name='notifications.email_loan_rejected')
def task_email_loan_rejected(loan_id: int, reason: str = ''):
    from apps.loans.models import Loan
    from apps.notifications.email_service import email_loan_rejected
    try:
        loan = Loan.objects.select_related('customer').get(id=loan_id)
        return email_loan_rejected(loan, reason)
    except Loan.DoesNotExist:
        pass


@shared_task(name='notifications.email_payment_received')
def task_email_payment_received(payment_id: int):
    from apps.payments.models import Payment
    from apps.notifications.email_service import email_payment_received
    try:
        payment = Payment.objects.select_related('loan__customer').get(id=payment_id)
        return email_payment_received(payment)
    except Payment.DoesNotExist:
        pass


@shared_task(name='notifications.email_staff_welcome')
def task_email_staff_welcome(user_id: int, temp_password: str):
    from apps.accounts.models import User
    from apps.notifications.email_service import email_staff_new_account
    try:
        user = User.objects.get(id=user_id)
        return email_staff_new_account(user, temp_password)
    except User.DoesNotExist:
        pass


# ══════════════════════════════════════════════════════════════
#  SCHEDULED TASKS (run via Celery Beat)
# ══════════════════════════════════════════════════════════════

@shared_task(name='notifications.daily_payment_reminders')
def task_daily_payment_reminders():
    """
    Runs daily at 8 AM EAT.
    Sends SMS reminders for loans due in 1, 3, and 7 days.
    """
    from apps.loans.models import Loan
    from apps.notifications.sms import sms_payment_reminder

    today = timezone.now().date()
    reminder_days = [1, 3, 7]
    sent = 0

    for days in reminder_days:
        target_date = today + timedelta(days=days)
        loans = Loan.objects.filter(
            status='ACTIVE',
            due_date=target_date,
        ).select_related('customer', 'loan_officer')
        for loan in loans:
            try:
                sms_payment_reminder(loan)
                sent += 1
            except Exception as e:
                logger.error(f'Reminder SMS failed for {loan.loan_id}: {e}')

    logger.info(f'[SCHEDULED] Payment reminders sent: {sent}')
    return {'sent': sent, 'date': str(today)}


@shared_task(name='notifications.daily_overdue_chase')
def task_daily_overdue_chase():
    """
    Runs daily at 9 AM EAT.
    Sends overdue notices and applies daily penalties.
    """
    from apps.loans.models import Loan
    from apps.notifications.sms import sms_overdue
    from apps.notifications.email_service import email_overdue_notice
    from decimal import Decimal

    today = timezone.now().date()
    overdue = Loan.objects.filter(
        status='ACTIVE',
        due_date__lt=today,
    ).select_related('customer', 'loan_officer', 'product')

    processed = 0
    for loan in overdue:
        days_overdue = (today - loan.due_date).days
        try:
            # Apply daily penalty
            daily_rate   = loan.product.penalty_rate / Decimal('100')
            penalty_today = loan.balance * daily_rate
            loan.penalty_amount = loan.penalty_amount + penalty_today
            loan.balance        = loan.balance + penalty_today
            loan.save(update_fields=['penalty_amount', 'balance'])

            # SMS
            sms_overdue(loan, days_overdue)

            # Email for severe cases (>7 days)
            if days_overdue > 7:
                email_overdue_notice(loan, days_overdue)

            processed += 1
        except Exception as e:
            logger.error(f'Overdue processing failed for {loan.loan_id}: {e}')

    logger.info(f'[SCHEDULED] Overdue processed: {processed} loans | date: {today}')
    return {'processed': processed, 'date': str(today)}


@shared_task(name='notifications.weekly_portfolio_report')
def task_weekly_portfolio_report():
    """
    Runs every Monday at 7 AM EAT.
    Emails branch managers a portfolio summary.
    """
    from apps.accounts.models import User
    from apps.loans.models import Loan
    from apps.payments.models import Payment
    from apps.notifications.email_service import send_email, _html_wrapper
    from django.db.models import Sum, Count

    today       = timezone.now().date()
    week_start  = today - timedelta(days=7)

    managers = User.objects.filter(
        role__in=['SUPER_ADMIN', 'BRANCH_MANAGER'],
        is_active=True,
    ).select_related('branch')

    for manager in managers:
        if not manager.email:
            continue
        branch_filter = {'branch': manager.branch} if manager.branch else {}

        loans   = Loan.objects.filter(**branch_filter)
        active  = loans.filter(status='ACTIVE').count()
        default = loans.filter(status='DEFAULT').count()
        new_this_week = loans.filter(created_at__date__gte=week_start).count()
        mtd_pay = Payment.objects.filter(
            loan__in=loans,
            paid_at__date__gte=week_start,
        ).aggregate(total=Sum('amount'))['total'] or 0

        subject = f'QuickLender Weekly Portfolio — {today.strftime("%d %b %Y")}'
        text = (
            f'Weekly portfolio summary for {manager.full_name}.\n'
            f'Active: {active} | Defaults: {default} | New: {new_this_week} | Collections: KES {mtd_pay:,.0f}'
        )
        html_body = f"""
            <h2>Weekly Portfolio Report</h2>
            <p>Hi <strong>{manager.full_name}</strong>, here's your portfolio summary for the week ending {today.strftime('%d %B %Y')}:</p>
            <table class="info-table">
              <tr><td>Active Loans</td><td>{active}</td></tr>
              <tr><td>Defaulted Loans</td><td style="color:#991b1b;font-weight:700">{default}</td></tr>
              <tr><td>New Loans (7 days)</td><td>{new_this_week}</td></tr>
              <tr><td>Collections (7 days)</td><td>KES {float(mtd_pay):,.0f}</td></tr>
            </table>
            <p style="font-size:13px;color:#6b7280">Log in to QuickLender for full details and reports.</p>
        """
        try:
            send_email(manager.email, subject, text, _html_wrapper(subject, html_body))
        except Exception as e:
            logger.error(f'Weekly report failed for {manager.email}: {e}')

    logger.info(f'[SCHEDULED] Weekly report sent to {managers.count()} managers')
    return {'managers': managers.count(), 'date': str(today)}


@shared_task(name='notifications.mark_dormant_customers')
def task_mark_dormant_customers():
    """
    Runs monthly on the 1st.
    Mark customers as DORMANT if no loan activity in 90 days.
    """
    from apps.customers.models import Customer
    from apps.loans.models import Loan

    cutoff = timezone.now() - timedelta(days=90)
    active_customers = Loan.objects.filter(
        status__in=['ACTIVE', 'PENDING', 'APPROVED'],
    ).values_list('customer_id', flat=True)

    recently_active = Loan.objects.filter(
        updated_at__gte=cutoff,
    ).values_list('customer_id', flat=True)

    dormant = Customer.objects.filter(
        status='ACTIVE',
    ).exclude(id__in=active_customers).exclude(id__in=recently_active)

    count = dormant.update(status='DORMANT')
    logger.info(f'[SCHEDULED] Marked {count} customers as DORMANT')
    return {'dormant_count': count}


@shared_task(name='notifications.reconcile_mpesa_transactions')
def task_reconcile_mpesa():
    """
    Runs every 15 minutes.
    Checks PENDING M-Pesa transactions and queries Daraja for status.
    """
    from apps.payments.models import MpesaTransaction
    from apps.payments.mpesa import query_stk_status

    pending = MpesaTransaction.objects.filter(
        status='PENDING',
        txn_type='STK',
        initiated_at__gte=timezone.now() - timedelta(hours=1),  # only recent ones
    )

    updated = 0
    for txn in pending:
        if not txn.conversation_id:
            continue
        try:
            result = query_stk_status(txn.conversation_id)
            result_code = result.get('ResultCode')
            if result_code == 0:
                txn.status       = 'SUCCESS'
                txn.result_desc  = result.get('ResultDesc', '')
                txn.completed_at = timezone.now()
                txn.save()
                updated += 1
            elif result_code is not None and result_code != 0:
                txn.status      = 'FAILED'
                txn.result_desc = result.get('ResultDesc', '')
                txn.save()
                updated += 1
        except Exception as e:
            logger.warning(f'M-Pesa query failed for {txn.conversation_id}: {e}')

    logger.info(f'[RECONCILE] M-Pesa: {updated} transactions updated')
    return {'updated': updated}


@shared_task(name='loans.check_arrears')
def task_check_arrears():
    """
    Daily task (runs 09:00 EAT alongside penalty engine).
    For every ACTIVE loan:
      - Check how many consecutive installments are unpaid and past due.
      - Update loan.arrears_count.
      - If arrears_count reaches 3, fire apply_arrears_rate() → rate → 21%.
      - Trigger tier recalculation for the customer.
    """
    from apps.loans.models import Loan, RepaymentSchedule
    from apps.loans.pricing import apply_arrears_rate, recalculate_and_save_tier
    from django.utils import timezone

    today = timezone.now().date()
    active_loans = Loan.objects.filter(status='ACTIVE').select_related('customer', 'product')

    promoted = 0
    rate_raised = 0

    for loan in active_loans.iterator(chunk_size=200):
        # Count consecutive overdue unpaid installments (if schedule exists)
        overdue_rows = RepaymentSchedule.objects.filter(
            loan=loan,
            status='PENDING',
            due_date__lt=today,
        ).count()

        if overdue_rows != loan.arrears_count:
            loan.arrears_count = overdue_rows
            loan.save(update_fields=['arrears_count'])

        if overdue_rows >= 3:
            if apply_arrears_rate(loan):
                rate_raised += 1
            # Recalculate tier (may demote)
            result = recalculate_and_save_tier(loan.customer)
            if result['changed']:
                promoted += 1

    logger.info(
        f'[task_check_arrears] checked {active_loans.count()} active loans — '
        f'{rate_raised} rate raised to 21%, {promoted} tier changes'
    )
