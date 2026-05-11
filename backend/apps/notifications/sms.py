"""
notifications/sms.py
Africa's Talking SMS integration with template rendering.
"""
import logging
import re
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger('apps.notifications')

# ─── SMS TEMPLATES ────────────────────────────────────────────────────────────
TEMPLATES = {
    'DISBURSEMENT': (
        "Dear {name}, your QuickLender loan of KES {amount} ({loan_id}) has been "
        "disbursed to {phone}. Repayment of KES {total} due by {due_date}. "
        "Questions? Call 0800-720-QL. -QuickLender"
    ),
    'PAYMENT_CONFIRM': (
        "Dear {name}, payment of KES {amount} received for loan {loan_id}. "
        "Outstanding balance: KES {balance}. Thank you! -QuickLender"
    ),
    'PAYMENT_REMINDER': (
        "Dear {name}, your loan {loan_id} repayment of KES {amount} is due on "
        "{due_date}. Pay via M-Pesa Paybill {shortcode} Acc: {loan_id}. "
        "Avoid penalty charges. -QuickLender"
    ),
    'OVERDUE_1': (
        "Dear {name}, your loan {loan_id} (KES {balance}) is {days} day(s) overdue. "
        "Please pay immediately to avoid penalties. Call {officer_phone}. -QuickLender"
    ),
    'OVERDUE_2': (
        "URGENT: Dear {name}, loan {loan_id} is {days} days overdue. "
        "Balance: KES {balance} + penalties accruing daily. "
        "Call {officer_phone} immediately or visit your branch. -QuickLender"
    ),
    'OVERDUE_3': (
        "FINAL NOTICE: Dear {name}, loan {loan_id} ({days} days overdue, "
        "KES {balance}) is being escalated for legal recovery. "
        "Call 0800-720-QL within 48hrs to arrange repayment. -QuickLender"
    ),
    'APPROVAL': (
        "Congratulations {name}! Your QuickLender loan application {loan_id} "
        "for KES {amount} has been APPROVED. You will receive disbursement shortly. "
        "-QuickLender"
    ),
    'REJECTION': (
        "Dear {name}, your loan application {loan_id} was not approved at this time. "
        "Visit your branch for details. You may reapply after 30 days. -QuickLender"
    ),
}


def render_template(template_key: str, context: dict) -> str:
    """Render an SMS template with context variables."""
    template = TEMPLATES.get(template_key, '{message}')
    try:
        return template.format(**context)
    except KeyError as e:
        logger.warning(f'SMS template {template_key} missing key {e}')
        return template  # Return unrendered as fallback


def normalize_phone(phone: str) -> str | None:
    """Normalize a Kenyan phone number to 254XXXXXXXXX format."""
    if not phone:
        return None
    phone = re.sub(r'[\s\-\(\)]', '', str(phone))
    phone = phone.lstrip('+')
    if re.match(r'^07\d{8}$', phone):
        return '254' + phone[1:]
    if re.match(r'^01\d{8}$', phone):
        return '254' + phone[1:]
    if re.match(r'^2547\d{8}$', phone):
        return phone
    if re.match(r'^2541\d{8}$', phone):
        return phone
    return None


def send_sms(phone: str, message: str, customer=None, loan=None, template_key: str = 'CUSTOM') -> dict:
    """
    Send an SMS via Africa's Talking API and log the result.

    Returns:
        dict with keys: success, message_id, cost, error
    """
    from apps.notifications.models import SMSLog

    norm_phone = normalize_phone(phone)
    if not norm_phone:
        logger.error(f'Invalid phone number: {phone}')
        return {'success': False, 'error': f'Invalid phone: {phone}'}

    log = SMSLog.objects.create(
        recipient=norm_phone,
        customer=customer,
        loan=loan,
        template=template_key,
        message=message,
        status=SMSLog.Status.PENDING,
    )

    # Check if AT credentials are configured
    api_key  = getattr(settings, 'AT_API_KEY', '')
    username = getattr(settings, 'AT_USERNAME', 'sandbox')

    if not api_key or api_key == 'your_at_api_key_here':
        # Sandbox/dev mode — log but don't call API
        logger.info(f'[SMS DEV] To {norm_phone}: {message}')
        log.status   = SMSLog.Status.SENT
        log.sent_at  = timezone.now()
        log.at_message_id = 'DEV-MODE'
        log.at_cost  = 'KES 0.00 (dev)'
        log.save()
        return {'success': True, 'message_id': 'DEV-MODE', 'cost': '0', 'dev_mode': True}

    # Live Africa's Talking call
    try:
        import requests
        url = (
            'https://api.africastalking.com/version1/messaging'
            if username != 'sandbox'
            else 'https://api.sandbox.africastalking.com/version1/messaging'
        )
        headers = {
            'apiKey': api_key,
            'Accept': 'application/json',
            'Content-Type': 'application/x-www-form-urlencoded',
        }
        payload = {
            'username': username,
            'to':       f'+{norm_phone}',
            'message':  message,
            'from':     getattr(settings, 'AT_SENDER_ID', 'QuickLndr'),
        }
        resp = requests.post(url, data=payload, headers=headers, timeout=15)
        data = resp.json()

        recipients = data.get('SMSMessageData', {}).get('Recipients', [])
        if recipients:
            r = recipients[0]
            status_code = r.get('statusCode', 0)
            if status_code == 101:
                log.status       = SMSLog.Status.SENT
                log.sent_at      = timezone.now()
                log.at_message_id= r.get('messageId', '')
                log.at_cost      = r.get('cost', '')
                log.save()
                logger.info(f'SMS sent to {norm_phone} | ID: {log.at_message_id} | Cost: {log.at_cost}')
                return {'success': True, 'message_id': log.at_message_id, 'cost': log.at_cost}
            else:
                raise Exception(r.get('status', 'Unknown AT error'))
        else:
            raise Exception(data.get('SMSMessageData', {}).get('Message', 'No recipients'))

    except Exception as e:
        log.status         = SMSLog.Status.FAILED
        log.failure_reason = str(e)
        log.save()
        logger.error(f'SMS failed to {norm_phone}: {e}')
        return {'success': False, 'error': str(e)}


# ─── CONVENIENCE SENDERS ──────────────────────────────────────────────────────

def sms_loan_disbursed(loan):
    """Send SMS when a loan is disbursed."""
    ctx = {
        'name':     loan.customer.first_name,
        'amount':   f'{float(loan.principal):,.0f}',
        'loan_id':  loan.loan_id,
        'phone':    loan.customer.phone,
        'total':    f'{float(loan.total_amount):,.0f}',
        'due_date': loan.due_date.strftime('%d %b %Y') if loan.due_date else 'N/A',
        'shortcode': getattr(settings, 'MPESA_SHORTCODE', '174379'),
    }
    msg = render_template('DISBURSEMENT', ctx)
    return send_sms(loan.customer.phone, msg, customer=loan.customer, loan=loan, template_key='DISBURSEMENT')


def sms_payment_confirmed(payment):
    """Send SMS when a payment is recorded."""
    loan = payment.loan
    ctx = {
        'name':    loan.customer.first_name,
        'amount':  f'{float(payment.amount):,.0f}',
        'loan_id': loan.loan_id,
        'balance': f'{float(loan.balance):,.0f}',
    }
    msg = render_template('PAYMENT_CONFIRM', ctx)
    return send_sms(loan.customer.phone, msg, customer=loan.customer, loan=loan, template_key='PAYMENT_CONFIRM')


def sms_loan_approved(loan):
    ctx = {
        'name':    loan.customer.first_name,
        'loan_id': loan.loan_id,
        'amount':  f'{float(loan.principal):,.0f}',
    }
    msg = render_template('APPROVAL', ctx)
    return send_sms(loan.customer.phone, msg, customer=loan.customer, loan=loan, template_key='APPROVAL')


def sms_loan_rejected(loan):
    ctx = {'name': loan.customer.first_name, 'loan_id': loan.loan_id}
    msg = render_template('REJECTION', ctx)
    return send_sms(loan.customer.phone, msg, customer=loan.customer, loan=loan, template_key='REJECTION')


def sms_payment_reminder(loan):
    """Send payment reminder for upcoming due loans."""
    ctx = {
        'name':     loan.customer.first_name,
        'loan_id':  loan.loan_id,
        'amount':   f'{float(loan.balance):,.0f}',
        'due_date': loan.due_date.strftime('%d %b %Y') if loan.due_date else 'N/A',
        'shortcode': getattr(settings, 'MPESA_SHORTCODE', '174379'),
    }
    msg = render_template('PAYMENT_REMINDER', ctx)
    return send_sms(loan.customer.phone, msg, customer=loan.customer, loan=loan, template_key='PAYMENT_REMINDER')


def sms_overdue(loan, days_overdue: int):
    """Send overdue notice based on severity."""
    if days_overdue <= 7:
        tpl = 'OVERDUE_1'
    elif days_overdue <= 30:
        tpl = 'OVERDUE_2'
    else:
        tpl = 'OVERDUE_3'

    officer = loan.loan_officer
    ctx = {
        'name':          loan.customer.first_name,
        'loan_id':       loan.loan_id,
        'balance':       f'{float(loan.balance):,.0f}',
        'days':          days_overdue,
        'officer_phone': officer.phone if officer and officer.phone else '0800-720-QL',
    }
    msg = render_template(tpl, ctx)
    return send_sms(loan.customer.phone, msg, customer=loan.customer, loan=loan, template_key=tpl)
