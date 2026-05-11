"""
notifications/email_service.py
Email notification service using Django's email backend.
"""
import logging
from django.conf import settings
from django.core.mail import send_mail, EmailMultiAlternatives
from django.utils import timezone

logger = logging.getLogger('apps.notifications')

# ─── EMAIL TEMPLATES ──────────────────────────────────────────────────────────

def _html_wrapper(title: str, body_html: str) -> str:
    """Wrap email body in QuickLender-branded HTML template."""
    return f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<style>
  body {{ font-family: 'Helvetica Neue', Arial, sans-serif; background: #f5f7fa; margin: 0; padding: 20px; }}
  .container {{ max-width: 580px; margin: 0 auto; background: #ffffff; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.08); }}
  .header {{ background: #0d1017; padding: 24px 32px; display: flex; align-items: center; }}
  .brand {{ color: #22d3a0; font-size: 22px; font-weight: 700; letter-spacing: -0.5px; }}
  .brand span {{ color: #ffffff; }}
  .body {{ padding: 32px; color: #374151; line-height: 1.6; }}
  .body h2 {{ color: #111827; font-size: 20px; margin: 0 0 16px; }}
  .highlight {{ background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 6px; padding: 16px; margin: 16px 0; }}
  .amount {{ font-size: 28px; font-weight: 700; color: #22d3a0; font-family: monospace; }}
  .info-table {{ width: 100%; border-collapse: collapse; margin: 16px 0; }}
  .info-table td {{ padding: 8px 0; border-bottom: 1px solid #f3f4f6; font-size: 14px; }}
  .info-table td:first-child {{ color: #6b7280; width: 45%; }}
  .info-table td:last-child {{ font-weight: 600; color: #111827; text-align: right; }}
  .btn {{ display: inline-block; background: #22d3a0; color: #0d1017; padding: 12px 24px; border-radius: 6px; text-decoration: none; font-weight: 700; margin: 16px 0; }}
  .footer {{ background: #f9fafb; padding: 20px 32px; font-size: 12px; color: #9ca3af; border-top: 1px solid #e5e7eb; }}
  .alert {{ background: #fff7ed; border: 1px solid #fed7aa; border-radius: 6px; padding: 16px; margin: 16px 0; color: #92400e; }}
  .danger {{ background: #fef2f2; border-color: #fecaca; color: #991b1b; }}
</style>
</head>
<body>
<div class="container">
  <div class="header"><div class="brand">Quick<span>Lender</span></div></div>
  <div class="body">{body_html}</div>
  <div class="footer">
    <p>QuickLender Ltd · CBK Licensed Microfinance Institution</p>
    <p>P.O Box 12345, Nairobi · 0800 720 QL · support@quicklender.co.ke</p>
    <p style="margin-top:8px;font-size:11px">This is an automated message. Do not reply directly to this email.</p>
  </div>
</div>
</body></html>"""


def send_email(recipient: str, subject: str, body_text: str, body_html: str = None) -> dict:
    """Send a single email and log it."""
    from apps.notifications.models import EmailLog

    log = EmailLog.objects.create(
        recipient=recipient,
        subject=subject,
        body_text=body_text,
        status='PENDING',
    )

    try:
        if body_html:
            msg = EmailMultiAlternatives(
                subject=subject,
                body=body_text,
                from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@quicklender.co.ke'),
                to=[recipient],
            )
            msg.attach_alternative(body_html, 'text/html')
            msg.send()
        else:
            send_mail(
                subject=subject,
                message=body_text,
                from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@quicklender.co.ke'),
                recipient_list=[recipient],
                fail_silently=False,
            )
        log.status  = 'SENT'
        log.sent_at = timezone.now()
        log.save()
        logger.info(f'Email sent to {recipient}: {subject}')
        return {'success': True}
    except Exception as e:
        log.status = 'FAILED'
        log.error  = str(e)
        log.save()
        logger.error(f'Email failed to {recipient}: {e}')
        return {'success': False, 'error': str(e)}


# ─── TEMPLATE EMAILS ──────────────────────────────────────────────────────────

def email_loan_disbursed(loan):
    """Email customer when loan is disbursed."""
    if not loan.customer.email:
        return {'skipped': True}
    subject = f'QuickLender — Loan Disbursed: {loan.loan_id}'
    text = (
        f"Dear {loan.customer.full_name},\n\n"
        f"Your loan of KES {float(loan.principal):,.0f} ({loan.loan_id}) has been disbursed.\n"
        f"Total repayable: KES {float(loan.total_amount):,.0f} by {loan.due_date}.\n\n"
        f"Pay via M-Pesa Paybill {settings.MPESA_SHORTCODE}, Account: {loan.loan_id}.\n\n"
        f"— QuickLender Team"
    )
    html_body = f"""
        <h2>Loan Disbursed Successfully</h2>
        <p>Dear <strong>{loan.customer.full_name}</strong>,</p>
        <p>Your QuickLender loan has been approved and disbursed to your M-Pesa account.</p>
        <div class="highlight">
          <div class="amount">KES {float(loan.principal):,.0f}</div>
          <div style="color:#6b7280;font-size:14px;margin-top:4px">Loan Reference: {loan.loan_id}</div>
        </div>
        <table class="info-table">
          <tr><td>Total Repayable</td><td>KES {float(loan.total_amount):,.0f}</td></tr>
          <tr><td>Interest ({loan.interest_rate}%)</td><td>KES {float(loan.interest_amount):,.0f}</td></tr>
          <tr><td>Due Date</td><td>{loan.due_date.strftime('%d %B %Y') if loan.due_date else 'N/A'}</td></tr>
          <tr><td>M-Pesa Paybill</td><td>{getattr(settings,'MPESA_SHORTCODE','174379')}</td></tr>
          <tr><td>Account Number</td><td>{loan.loan_id}</td></tr>
        </table>
        <p style="font-size:13px;color:#6b7280">Questions? Visit your branch or call 0800-720-QL</p>
    """
    return send_email(loan.customer.email, subject, text, _html_wrapper(subject, html_body))


def email_loan_approved(loan):
    if not loan.customer.email:
        return {'skipped': True}
    subject = f'QuickLender — Loan Application Approved: {loan.loan_id}'
    text = (
        f"Dear {loan.customer.full_name},\n\n"
        f"Great news! Your loan application {loan.loan_id} for KES {float(loan.principal):,.0f} "
        f"has been APPROVED.\n\nDisbursement will be processed shortly.\n\n— QuickLender"
    )
    html_body = f"""
        <h2>Application Approved! 🎉</h2>
        <p>Dear <strong>{loan.customer.full_name}</strong>,</p>
        <p>Your loan application has been reviewed and <strong>approved</strong> by our credit team.</p>
        <div class="highlight">
          <div class="amount">KES {float(loan.principal):,.0f}</div>
          <div style="color:#6b7280;font-size:14px;margin-top:4px">Reference: {loan.loan_id} — Disbursement pending</div>
        </div>
        <p>You will receive your funds shortly via M-Pesa. Watch out for a confirmation SMS.</p>
    """
    return send_email(loan.customer.email, subject, text, _html_wrapper(subject, html_body))


def email_loan_rejected(loan, reason: str = ''):
    if not loan.customer.email:
        return {'skipped': True}
    subject = f'QuickLender — Loan Application Update: {loan.loan_id}'
    text = (
        f"Dear {loan.customer.full_name},\n\n"
        f"Your loan application {loan.loan_id} was not approved at this time.\n"
        f"{('Reason: ' + reason) if reason else ''}\n\n"
        f"You may reapply after 30 days. Visit your branch for guidance.\n\n— QuickLender"
    )
    html_body = f"""
        <h2>Application Status Update</h2>
        <p>Dear <strong>{loan.customer.full_name}</strong>,</p>
        <div class="alert danger">
          <strong>Your loan application {loan.loan_id} was not approved</strong> at this time.
          {f'<p style="margin-top:8px">Reason: {reason}</p>' if reason else ''}
        </div>
        <p>This does not affect your future eligibility. You may reapply after 30 days or
        visit your branch to discuss alternative options with your Loan Officer.</p>
    """
    return send_email(loan.customer.email, subject, text, _html_wrapper(subject, html_body))


def email_payment_received(payment):
    loan = payment.loan
    if not loan.customer.email:
        return {'skipped': True}
    subject = f'QuickLender — Payment Received: {payment.ref}'
    text = (
        f"Dear {loan.customer.full_name},\n\n"
        f"Payment of KES {float(payment.amount):,.0f} has been received for loan {loan.loan_id}.\n"
        f"Outstanding balance: KES {float(loan.balance):,.0f}.\n\n— QuickLender"
    )
    is_cleared = float(loan.balance) <= 0
    html_body = f"""
        <h2>Payment Received</h2>
        <p>Dear <strong>{loan.customer.full_name}</strong>,</p>
        <p>We've received your payment. Here's your updated account summary:</p>
        <div class="highlight">
          <div class="amount">KES {float(payment.amount):,.0f}</div>
          <div style="color:#6b7280;font-size:14px;margin-top:4px">Reference: {payment.ref}</div>
        </div>
        <table class="info-table">
          <tr><td>Loan</td><td>{loan.loan_id}</td></tr>
          <tr><td>Payment Method</td><td>{payment.method}</td></tr>
          {f'<tr><td>M-Pesa Ref</td><td>{payment.mpesa_ref}</td></tr>' if payment.mpesa_ref else ''}
          <tr><td>Outstanding Balance</td><td>KES {float(loan.balance):,.0f}</td></tr>
        </table>
        {'''<div class="highlight" style="text-align:center">
          <div style="font-size:20px;font-weight:700;color:#22d3a0">🎉 Loan Fully Cleared!</div>
          <p style="color:#6b7280;margin-top:8px">Thank you for timely repayment. You are eligible for a new loan.</p>
        </div>''' if is_cleared else ''}
    """
    return send_email(loan.customer.email, subject, text, _html_wrapper(subject, html_body))


def email_overdue_notice(loan, days_overdue: int):
    if not loan.customer.email:
        return {'skipped': True}
    severity = 'FINAL NOTICE — ' if days_overdue > 30 else ''
    subject  = f'QuickLender — {severity}Loan Overdue: {loan.loan_id}'
    text = (
        f"Dear {loan.customer.full_name},\n\n"
        f"Loan {loan.loan_id} is {days_overdue} days overdue. "
        f"Outstanding balance: KES {float(loan.balance):,.0f}.\n\n"
        f"Please contact us urgently: 0800-720-QL\n\n— QuickLender"
    )
    colour  = '#991b1b' if days_overdue > 30 else '#92400e' if days_overdue > 7 else '#1d4ed8'
    bg      = '#fef2f2' if days_overdue > 30 else '#fff7ed' if days_overdue > 7 else '#eff6ff'
    border  = '#fecaca' if days_overdue > 30 else '#fed7aa' if days_overdue > 7 else '#bfdbfe'
    html_body = f"""
        <h2>Loan Repayment Overdue</h2>
        <p>Dear <strong>{loan.customer.full_name}</strong>,</p>
        <div class="alert" style="background:{bg};border-color:{border};color:{colour}">
          <strong>Loan {loan.loan_id} is {days_overdue} days overdue.</strong><br>
          {'Legal recovery proceedings may be initiated if not settled within 48 hours.' if days_overdue > 30 else 'Please settle your account immediately to avoid further penalties.'}
        </div>
        <table class="info-table">
          <tr><td>Loan Reference</td><td>{loan.loan_id}</td></tr>
          <tr><td>Outstanding Balance</td><td>KES {float(loan.balance):,.0f}</td></tr>
          <tr><td>Days Overdue</td><td><span style="color:{colour};font-weight:700">{days_overdue} days</span></td></tr>
          <tr><td>Daily Penalty Rate</td><td>{loan.product.penalty_rate}% per day</td></tr>
        </table>
        <p><strong>Pay now via:</strong><br>
        M-Pesa → Paybill {getattr(settings,'MPESA_SHORTCODE','174379')} → Account: {loan.loan_id}<br>
        Or call 0800-720-QL</p>
    """
    return send_email(loan.customer.email, subject, text, _html_wrapper(subject, html_body))


def email_staff_new_account(user, temp_password: str):
    """Send login credentials to a newly created staff member."""
    if not user.email:
        return {'skipped': True}
    subject  = 'Welcome to QuickLender — Your Account is Ready'
    text = (
        f"Dear {user.full_name},\n\n"
        f"Your QuickLender staff account has been created.\n"
        f"Email: {user.email}\nTemporary Password: {temp_password}\n\n"
        f"Please log in and change your password immediately.\n\n— QuickLender Admin"
    )
    html_body = f"""
        <h2>Welcome to QuickLender!</h2>
        <p>Dear <strong>{user.full_name}</strong>,</p>
        <p>Your staff account has been created. Here are your login credentials:</p>
        <div class="highlight">
          <table class="info-table">
            <tr><td>Email</td><td>{user.email}</td></tr>
            <tr><td>Temp Password</td><td style="font-family:monospace;letter-spacing:2px">{temp_password}</td></tr>
            <tr><td>Role</td><td>{user.role.replace('_',' ')}</td></tr>
            <tr><td>Staff ID</td><td>{user.staff_id}</td></tr>
          </table>
        </div>
        <p><strong>Important:</strong> Please change your password after your first login.</p>
        <a href="#" class="btn">Login to QuickLender</a>
    """
    return send_email(user.email, subject, text, _html_wrapper(subject, html_body))
