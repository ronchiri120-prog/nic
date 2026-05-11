"""
documents/generators.py
Generates HTML documents that can be printed or downloaded as PDF.

Documents:
  - Customer Account Statement (full transaction history)
  - Loan Agreement / Contract
  - Loan Disbursement Letter
  - Collection Notice (demand letter)
"""
from django.utils import timezone
from decimal import Decimal


def _currency(amount):
    try:
        v = float(amount or 0)
        return f'KES {v:,.2f}'
    except:
        return 'KES 0.00'


def _date(d):
    if not d: return '—'
    try:
        if hasattr(d, 'strftime'): return d.strftime('%d %B %Y')
        from datetime import date
        return date.fromisoformat(str(d)).strftime('%d %B %Y')
    except: return str(d)


def _html_doc(title: str, body: str, company='QuickLender Ltd') -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>{title} — {company}</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ font-family: 'Arial', sans-serif; font-size: 12px; color: #1a1a1a;
           background: #fff; padding: 32px; max-width: 800px; margin: 0 auto; }}
    .header {{ border-bottom: 3px solid #0d1017; padding-bottom: 16px; margin-bottom: 24px;
               display: flex; justify-content: space-between; align-items: flex-end; }}
    .brand {{ font-size: 22px; font-weight: 700; letter-spacing: -0.5px; }}
    .brand span {{ color: #22d3a0; }}
    .doc-title {{ font-size: 16px; font-weight: 700; color: #0d1017; text-align: right; }}
    .doc-ref {{ font-size: 10px; color: #666; text-align: right; }}
    .section {{ margin-bottom: 24px; }}
    .section-title {{ font-size: 11px; font-weight: 700; letter-spacing: 1.5px;
                      text-transform: uppercase; color: #888; padding-bottom: 6px;
                      border-bottom: 1px solid #e0e0e0; margin-bottom: 12px; }}
    .info-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 8px 24px; }}
    .info-row {{ display: flex; flex-direction: column; }}
    .info-label {{ font-size: 9px; text-transform: uppercase; letter-spacing: 1px; color: #888; }}
    .info-value {{ font-size: 12px; font-weight: 600; margin-top: 2px; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 11px; margin-top: 8px; }}
    th {{ background: #0d1017; color: #fff; padding: 6px 10px; text-align: left;
          font-size: 10px; letter-spacing: 0.5px; }}
    td {{ padding: 6px 10px; border-bottom: 1px solid #f0f0f0; }}
    tr:nth-child(even) td {{ background: #fafafa; }}
    .amount {{ text-align: right; font-family: 'Courier New', monospace; }}
    .total-row td {{ background: #0d1017 !important; color: #fff; font-weight: 700; }}
    .green {{ color: #0ea271; }}
    .red {{ color: #dc2626; }}
    .footer {{ border-top: 1px solid #e0e0e0; padding-top: 16px; margin-top: 32px;
               font-size: 10px; color: #888; text-align: center; }}
    .signature-block {{ display: grid; grid-template-columns: 1fr 1fr; gap: 48px; margin-top: 48px; }}
    .sig-line {{ border-top: 1px solid #0d1017; padding-top: 6px; font-size: 10px; color: #666; }}
    .stamp {{ width: 80px; height: 80px; border: 2px solid #e0e0e0; border-radius: 50%;
              display: flex; align-items: center; justify-content: center;
              font-size: 9px; color: #ccc; text-align: center; margin: 24px auto 0; }}
    @media print {{
      body {{ padding: 0; }}
      .no-print {{ display: none; }}
    }}
  </style>
</head>
<body>
  <div class="header">
    <div>
      <div class="brand">Quick<span>Lender</span></div>
      <div style="font-size:9px;color:#888;margin-top:3px">{company} · CBK Licensed MFI</div>
    </div>
    <div>
      <div class="doc-title">{title}</div>
      <div class="doc-ref">Generated: {timezone.now().strftime('%d %B %Y %H:%M EAT')}</div>
    </div>
  </div>
  {body}
  <div class="footer">
    {company} · This is a computer-generated document. For queries call 0800-720-QL or email support@quicklender.co.ke
  </div>
</body>
</html>"""


def customer_statement(customer, loans=None, payments=None, date_from=None, date_to=None) -> str:
    """Generate full account statement for a customer."""
    from apps.loans.models import Loan
    from apps.payments.models import Payment
    from django.db.models import Sum

    loans    = loans    or Loan.objects.filter(customer=customer).select_related('product','branch').order_by('-created_at')
    payments = payments or Payment.objects.filter(loan__customer=customer).select_related('loan').order_by('-paid_at')

    if date_from:
        payments = payments.filter(paid_at__date__gte=date_from)
    if date_to:
        payments = payments.filter(paid_at__date__lte=date_to)

    total_borrowed  = float(loans.aggregate(s=Sum('principal'))['s'] or 0)
    total_paid      = float(payments.aggregate(s=Sum('amount'))['s'] or 0)
    active_balance  = float(loans.filter(status__in=['ACTIVE','DEFAULT'])
                            .aggregate(s=Sum('balance'))['s'] or 0)

    period_label = ''
    if date_from or date_to:
        period_label = f"{_date(date_from) if date_from else 'All time'} to {_date(date_to) if date_to else 'Present'}"

    loan_rows = ''.join(f"""
      <tr>
        <td class="amount" style="font-family:monospace">{l.loan_id}</td>
        <td>{l.product.name if l.product else '—'}</td>
        <td class="amount">{_currency(l.principal)}</td>
        <td class="amount">{_currency(l.total_paid)}</td>
        <td class="amount {'red' if float(l.balance)>0 else 'green'}">{_currency(l.balance)}</td>
        <td>{l.status}</td>
        <td>{_date(l.disbursed_at)}</td>
        <td>{_date(l.due_date)}</td>
      </tr>""" for l in loans)

    pay_rows = ''.join(f"""
      <tr>
        <td>{_date(p.paid_at)}</td>
        <td class="amount" style="font-family:monospace">{p.ref}</td>
        <td class="amount" style="font-family:monospace">{p.loan.loan_id if p.loan else '—'}</td>
        <td class="amount green">{_currency(p.amount)}</td>
        <td>{p.method}</td>
        <td style="font-family:monospace">{p.mpesa_ref or '—'}</td>
      </tr>""" for p in payments)

    body = f"""
      <div class="section">
        <div class="section-title">Customer Details</div>
        <div class="info-grid">
          <div class="info-row"><span class="info-label">Customer ID</span><span class="info-value">{customer.uid}</span></div>
          <div class="info-row"><span class="info-label">Full Name</span><span class="info-value">{customer.full_name}</span></div>
          <div class="info-row"><span class="info-label">National ID</span><span class="info-value">{customer.national_id}</span></div>
          <div class="info-row"><span class="info-label">Phone</span><span class="info-value">{customer.phone}</span></div>
          <div class="info-row"><span class="info-label">Branch</span><span class="info-value">{customer.branch.name if customer.branch else '—'}</span></div>
          <div class="info-row"><span class="info-label">Statement Period</span><span class="info-value">{period_label or 'Full History'}</span></div>
        </div>
      </div>

      <div class="section" style="background:#f9fafb;border:1px solid #e0e0e0;border-radius:6px;padding:14px 20px;margin-bottom:20px">
        <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:16px;text-align:center">
          <div><div class="info-label">Total Borrowed</div><div style="font-size:18px;font-weight:700;margin-top:4px">{_currency(total_borrowed)}</div></div>
          <div><div class="info-label">Total Repaid</div><div style="font-size:18px;font-weight:700;color:#0ea271;margin-top:4px">{_currency(total_paid)}</div></div>
          <div><div class="info-label">Outstanding</div><div style="font-size:18px;font-weight:700;color:{'#dc2626' if active_balance>0 else '#0ea271'};margin-top:4px">{_currency(active_balance)}</div></div>
        </div>
      </div>

      <div class="section">
        <div class="section-title">Loan History</div>
        <table>
          <thead><tr><th>Loan ID</th><th>Product</th><th>Principal</th><th>Paid</th><th>Balance</th><th>Status</th><th>Disbursed</th><th>Due</th></tr></thead>
          <tbody>{loan_rows or '<tr><td colspan="8" style="text-align:center;color:#888;padding:16px">No loans found</td></tr>'}</tbody>
        </table>
      </div>

      <div class="section">
        <div class="section-title">Payment History</div>
        <table>
          <thead><tr><th>Date</th><th>Reference</th><th>Loan ID</th><th>Amount</th><th>Method</th><th>M-Pesa Ref</th></tr></thead>
          <tbody>{pay_rows or '<tr><td colspan="6" style="text-align:center;color:#888;padding:16px">No payments found</td></tr>'}</tbody>
          {'<tr class="total-row"><td colspan="3">TOTAL PAYMENTS</td><td class="amount">' + _currency(total_paid) + '</td><td colspan="2"></td></tr>' if pay_rows else ''}
        </table>
      </div>"""

    return _html_doc('Customer Account Statement', body)


def loan_agreement(loan) -> str:
    """Generate a formal loan agreement document."""
    customer = loan.customer
    product  = loan.product

    today = timezone.now().date()

    body = f"""
      <div style="text-align:center;margin-bottom:28px">
        <div style="font-size:15px;font-weight:700;text-transform:uppercase;letter-spacing:1px">Loan Agreement</div>
        <div style="font-size:11px;color:#888;margin-top:4px">Agreement No: {loan.loan_id} · Date: {_date(today)}</div>
      </div>

      <div class="section">
        <div class="section-title">Parties to this Agreement</div>
        <p style="margin-bottom:8px">This Loan Agreement ("<b>Agreement</b>") is entered into on <b>{_date(today)}</b> between:</p>
        <p style="margin-bottom:8px"><b>LENDER:</b> QuickLender Ltd, a duly licensed Microfinance Institution
          (Registration No. [CBK/MFI/XXXX]), P.O Box XXXXX, Nairobi, Kenya
          ("<b>QuickLender</b>" or "<b>Lender</b>"); AND</p>
        <p><b>BORROWER:</b> <b>{customer.full_name}</b>, National ID No. <b>{customer.national_id}</b>,
          of {customer.address or '[Address]'}, ("<b>Borrower</b>").</p>
      </div>

      <div class="section">
        <div class="section-title">Loan Terms</div>
        <table>
          <tr><td style="width:50%"><b>Loan Reference</b></td><td class="amount" style="font-family:monospace"><b>{loan.loan_id}</b></td></tr>
          <tr><td><b>Loan Product</b></td><td>{product.name if product else '—'}</td></tr>
          <tr><td><b>Principal Amount</b></td><td class="amount"><b>{_currency(loan.principal)}</b></td></tr>
          <tr><td><b>Interest Rate</b></td><td>{float(loan.interest_rate)}% flat</td></tr>
          <tr><td><b>Interest Amount</b></td><td class="amount">{_currency(loan.interest_amount)}</td></tr>
          <tr><td><b>Total Repayable</b></td><td class="amount"><b style="color:#dc2626">{_currency(loan.total_amount)}</b></td></tr>
          <tr><td><b>Loan Tenure</b></td><td>{loan.tenure_days} days</td></tr>
          <tr><td><b>Disbursement Date</b></td><td>{_date(loan.disbursed_at)}</td></tr>
          <tr><td><b>Repayment Due Date</b></td><td><b>{_date(loan.due_date)}</b></td></tr>
          <tr><td><b>Disbursement Method</b></td><td>{loan.disbursement_method}</td></tr>
          <tr><td><b>Penalty Rate</b></td><td>{float(product.penalty_rate if product else 0.5)}% per day on overdue balance</td></tr>
        </table>
      </div>

      <div class="section">
        <div class="section-title">Repayment Instructions</div>
        <p style="margin-bottom:8px">The Borrower shall repay the full amount of <b>{_currency(loan.total_amount)}</b>
          on or before <b>{_date(loan.due_date)}</b> by:</p>
        <ol style="margin-left:20px;line-height:2">
          <li>M-Pesa PayBill: <b>[SHORTCODE]</b> — Account Number: <b>{loan.loan_id}</b></li>
          <li>Bank transfer to QuickLender Ltd account (contact branch for details)</li>
          <li>Cash payment at any QuickLender branch</li>
        </ol>
      </div>

      <div class="section">
        <div class="section-title">Penalties &amp; Default</div>
        <p>In the event of non-payment by the due date, a penalty of
          <b>{float(product.penalty_rate if product else 0.5)}% per day</b>
          shall accrue on the outstanding balance. The Lender reserves the right to
          report defaults to the Credit Reference Bureau (CRB), engage collection agents,
          and exercise any security held.</p>
      </div>

      <div class="section">
        <div class="section-title">Declarations</div>
        <p>The Borrower confirms that: (a) all information provided is true and correct;
          (b) they have read and understood these terms; (c) they accept the loan on the terms stated above.</p>
      </div>

      <div class="signature-block">
        <div>
          <div class="stamp">COMPANY STAMP</div>
          <div class="sig-line" style="margin-top:8px">
            Authorised Signatory<br>QuickLender Ltd<br>Name: ___________________<br>Date: {_date(today)}
          </div>
        </div>
        <div>
          <br><br><br><br>
          <div class="sig-line">
            Borrower's Signature / Thumbprint<br>Name: <b>{customer.full_name}</b><br>
            ID: {customer.national_id}<br>Date: {_date(today)}
          </div>
        </div>
      </div>"""

    return _html_doc('Loan Agreement', body)


def disbursement_letter(loan) -> str:
    """Formal disbursement letter to the customer."""
    customer = loan.customer
    body = f"""
      <div class="section">
        <p style="text-align:right;margin-bottom:16px">{_date(loan.disbursed_at or timezone.now())}</p>
        <p><b>{customer.full_name}</b><br>
        ID: {customer.national_id}<br>
        Phone: {customer.phone}<br>
        {customer.address or ''}</p>
      </div>
      <div class="section">
        <p style="margin-bottom:12px"><b>RE: LOAN DISBURSEMENT — {loan.loan_id}</b></p>
        <p style="margin-bottom:12px">Dear <b>{customer.first_name}</b>,</p>
        <p style="margin-bottom:12px">We are pleased to inform you that your loan application has been approved
          and the following amount has been disbursed to your M-Pesa account:</p>
        <div style="background:#0d1017;color:#fff;border-radius:8px;padding:20px;text-align:center;margin:20px 0">
          <div style="font-size:28px;font-weight:700;color:#22d3a0">{_currency(loan.principal)}</div>
          <div style="font-size:11px;color:#aaa;margin-top:4px">Loan Reference: {loan.loan_id}</div>
        </div>
        <table>
          <tr><td>Principal Disbursed</td><td class="amount">{_currency(loan.principal)}</td></tr>
          <tr><td>Interest Charged</td><td class="amount">{_currency(loan.interest_amount)}</td></tr>
          <tr><td><b>Total to Repay</b></td><td class="amount"><b>{_currency(loan.total_amount)}</b></td></tr>
          <tr><td><b>Repayment Due Date</b></td><td class="amount"><b>{_date(loan.due_date)}</b></td></tr>
        </table>
        <p style="margin-top:16px">To repay, use M-Pesa PayBill <b>[SHORTCODE]</b>, Account Number: <b>{loan.loan_id}</b>.</p>
        <p style="margin-top:8px">For any queries, please contact your Loan Officer or call <b>0800-720-QL</b>.</p>
        <p style="margin-top:16px">Yours sincerely,</p>
        <p style="margin-top:24px"><b>QuickLender Ltd</b><br>Credit Department</p>
      </div>"""
    return _html_doc('Loan Disbursement Letter', body)


def demand_letter(loan, days_overdue: int) -> str:
    """Formal demand / collection notice."""
    customer = loan.customer
    level    = 'FINAL NOTICE' if days_overdue > 30 else 'SECOND NOTICE' if days_overdue > 14 else 'FIRST NOTICE'
    body = f"""
      <div style="background:#dc2626;color:#fff;border-radius:6px;padding:10px 16px;
                  text-align:center;font-weight:700;letter-spacing:1px;margin-bottom:20px">
        {level} — OVERDUE LOAN RECOVERY
      </div>
      <div class="section">
        <p style="text-align:right">{_date(timezone.now().date())}</p>
        <p><b>{customer.full_name}</b><br>ID: {customer.national_id}<br>Phone: {customer.phone}</p>
      </div>
      <div class="section">
        <p style="margin-bottom:12px"><b>RE: DEMAND FOR REPAYMENT — {loan.loan_id} ({days_overdue} DAYS OVERDUE)</b></p>
        <p style="margin-bottom:12px">Dear <b>{customer.first_name}</b>,</p>
        <p style="margin-bottom:12px">Despite previous communications, your loan account remains overdue.
          This notice serves as formal demand for immediate settlement.</p>
        <table>
          <tr><td><b>Loan Reference</b></td><td class="amount red"><b>{loan.loan_id}</b></td></tr>
          <tr><td>Original Principal</td><td class="amount">{_currency(loan.principal)}</td></tr>
          <tr><td>Amount Already Paid</td><td class="amount green">{_currency(loan.total_paid)}</td></tr>
          <tr><td>Penalties Accrued</td><td class="amount red">{_currency(loan.penalty_amount)}</td></tr>
          <tr class="total-row"><td>OUTSTANDING BALANCE (incl. penalties)</td><td class="amount">{_currency(loan.balance)}</td></tr>
          <tr><td>Days Overdue</td><td class="amount red"><b>{days_overdue} days</b></td></tr>
        </table>
        <p style="margin-top:16px;color:#dc2626;font-weight:600">
          You are required to settle the full outstanding balance of <b>{_currency(loan.balance)}</b>
          within <b>{'48 hours' if days_overdue>30 else '7 days'}</b> of this notice.
        </p>
        {'<p style="margin-top:12px">Failure to respond will result in: (a) reporting to Credit Reference Bureau; (b) engagement of debt recovery agents; (c) legal action to recover the debt plus costs.</p>' if days_overdue > 14 else ''}
        <p style="margin-top:12px">To settle, use M-Pesa PayBill <b>[SHORTCODE]</b> → Account: <b>{loan.loan_id}</b>
          or contact us immediately on <b>0800-720-QL</b>.</p>
        <p style="margin-top:20px">Yours faithfully,</p>
        <p style="margin-top:24px"><b>Collections Department</b><br>QuickLender Ltd</p>
      </div>"""
    return _html_doc(f'Demand Notice — {level}', body)


def payment_receipt(payment) -> str:
    """Generate a printable payment receipt."""
    loan = payment.loan
    customer = loan.customer if loan else None

    body = f"""
      <div style="max-width:420px;margin:0 auto">
        <div style="text-align:center;padding:20px 0 16px">
          <div class="brand" style="font-size:26px;font-weight:700;letter-spacing:-0.5px">
            Quick<span style="color:#22d3a0">Lender</span>
          </div>
          <div style="font-size:11px;color:#888;margin-top:3px">Official Payment Receipt</div>
        </div>

        <div style="background:#0d1017;color:#fff;border-radius:10px;padding:20px;margin-bottom:20px;text-align:center">
          <div style="font-size:11px;color:#aaa;letter-spacing:1px;text-transform:uppercase;margin-bottom:6px">Amount Paid</div>
          <div style="font-size:36px;font-weight:700;color:#22d3a0;letter-spacing:-1px">{_currency(payment.amount)}</div>
          <div style="font-size:11px;color:#aaa;margin-top:4px">{_date(payment.paid_at)}</div>
        </div>

        <table>
          <tr><td><b>Receipt No.</b></td><td class="amount" style="font-family:monospace">{payment.ref}</td></tr>
          <tr><td><b>M-Pesa Ref</b></td><td class="amount" style="font-family:monospace">{payment.mpesa_ref or '—'}</td></tr>
          <tr><td><b>Loan Reference</b></td><td class="amount" style="font-family:monospace">{loan.loan_id if loan else '—'}</td></tr>
          <tr><td><b>Customer</b></td><td>{customer.full_name if customer else '—'}</td></tr>
          <tr><td><b>National ID</b></td><td style="font-family:monospace">{customer.national_id if customer else '—'}</td></tr>
          <tr><td><b>Phone</b></td><td style="font-family:monospace">{payment.phone or (customer.phone if customer else '—')}</td></tr>
          <tr><td><b>Method</b></td><td>{payment.method}</td></tr>
          <tr><td><b>Payment Type</b></td><td>{payment.payment_type}</td></tr>
          <tr><td><b>Remaining Balance</b></td><td class="amount {'red' if float(loan.balance)>0 else 'green'}">{_currency(loan.balance) if loan else '—'}</td></tr>
          <tr><td><b>Loan Status</b></td><td>{loan.status if loan else '—'}</td></tr>
        </table>

        <div style="margin-top:20px;padding:12px;background:#f9fafb;border-radius:6px;font-size:10px;color:#888;text-align:center">
          This is a computer-generated receipt. For queries contact your branch or call <b>0800-720-QL</b>.
        </div>
      </div>"""

    return _html_doc('Payment Receipt', body)
