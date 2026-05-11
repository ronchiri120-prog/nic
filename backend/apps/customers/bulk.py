"""
customers/bulk.py
Bulk import/export for field agents.

Import:  POST /api/v1/customers/bulk-import/   (multipart CSV)
Export:  GET  /api/v1/customers/export/         (returns CSV download)
         GET  /api/v1/loans/export/              (loans CSV)

CSV format — customers:
  first_name, last_name, national_id, phone, email, branch_code,
  monthly_income, loan_limit, employer, employment_type

CSV format — loans:
  loan_id, customer_uid, principal, interest_rate, tenure_days,
  status, due_date, balance, lo_email
"""
import csv
import io
from django.http import HttpResponse
from django.utils import timezone


CUSTOMER_HEADERS = [
    'first_name','last_name','national_id','phone','email',
    'branch_code','monthly_income','loan_limit','employer','employment_type',
]

LOAN_EXPORT_HEADERS = [
    'loan_id','customer_uid','customer_name','principal','interest_rate',
    'tenure_days','status','disbursed_at','due_date','total_paid','balance','lo_email',
]


def import_customers_csv(file_obj, branch, loan_officer, dry_run=False) -> dict:
    """
    Parse and import a customer CSV.
    Returns: { created, updated, errors, preview (first 5 rows) }
    """
    from apps.customers.models import Customer
    from apps.branches.models import Branch

    content = file_obj.read()
    if isinstance(content, bytes):
        content = content.decode('utf-8-sig')   # Handle BOM from Excel
    reader  = csv.DictReader(io.StringIO(content))

    created = 0
    updated = 0
    errors  = []
    preview = []

    for i, row in enumerate(reader, start=2):   # Row 1 = header
        row = {k.strip().lower().replace(' ','_'): v.strip() for k, v in row.items()}

        # Resolve branch
        branch_obj = branch
        if row.get('branch_code'):
            branch_obj = Branch.objects.filter(code__iexact=row['branch_code']).first() or branch

        # Validate required fields
        if not row.get('first_name') or not row.get('national_id') or not row.get('phone'):
            errors.append({'row': i, 'error': 'Missing first_name, national_id, or phone',
                           'data': dict(list(row.items())[:4])})
            continue

        if i <= 6:   # Preview first 5 rows
            preview.append(row)

        if dry_run:
            continue

        try:
            cust, was_created = Customer.objects.update_or_create(
                national_id=row['national_id'],
                defaults={
                    'first_name':      row.get('first_name', ''),
                    'last_name':       row.get('last_name', ''),
                    'phone':           row.get('phone', ''),
                    'email':           row.get('email', ''),
                    'branch':          branch_obj,
                    'loan_officer':    loan_officer,
                    'monthly_income':  float(row.get('monthly_income', 0) or 0),
                    'loan_limit':      float(row.get('loan_limit', 50000) or 50000),
                    'employer':        row.get('employer', ''),
                    'employment_type': row.get('employment_type', ''),
                },
            )
            if was_created: created += 1
            else:           updated += 1
        except Exception as e:
            errors.append({'row': i, 'error': str(e), 'national_id': row.get('national_id')})

    return {
        'created':     created,
        'updated':     updated,
        'errors':      errors,
        'error_count': len(errors),
        'preview':     preview,
        'dry_run':     dry_run,
    }


def export_customers_csv(queryset=None) -> HttpResponse:
    """Export customers to a downloadable CSV."""
    from apps.customers.models import Customer
    if queryset is None:
        queryset = Customer.objects.select_related('branch','loan_officer').all()

    response = HttpResponse(content_type='text/csv')
    filename = f'quicklender_customers_{timezone.now().strftime("%Y%m%d_%H%M")}.csv'
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    writer = csv.writer(response)
    writer.writerow([
        'UID','First Name','Last Name','National ID','Phone','Email',
        'Branch','Loan Officer','Monthly Income','Loan Limit',
        'Credit Score','Status','Registered',
    ])

    for c in queryset.iterator(chunk_size=500):
        writer.writerow([
            c.uid, c.first_name, c.last_name, c.national_id,
            c.phone, c.email or '',
            c.branch.name if c.branch else '',
            c.loan_officer.full_name if c.loan_officer else '',
            float(c.monthly_income or 0),
            float(c.loan_limit or 0),
            c.credit_score or 0,
            c.status,
            c.created_at.strftime('%Y-%m-%d'),
        ])
    return response


def export_loans_csv(queryset=None) -> HttpResponse:
    """Export loan portfolio to CSV."""
    from apps.loans.models import Loan
    if queryset is None:
        queryset = Loan.objects.select_related(
            'customer','product','branch','loan_officer'
        ).all()

    response = HttpResponse(content_type='text/csv')
    filename = f'quicklender_loans_{timezone.now().strftime("%Y%m%d_%H%M")}.csv'
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    writer = csv.writer(response)
    writer.writerow([
        'Loan ID','Customer UID','Customer Name','Product','Branch',
        'Principal','Interest Rate','Tenure Days','Status',
        'Disbursed At','Due Date','Total Paid','Balance',
        'Penalty','Loan Officer',
    ])

    for l in queryset.iterator(chunk_size=500):
        writer.writerow([
            l.loan_id,
            l.customer.uid if l.customer else '',
            l.customer.full_name if l.customer else '',
            l.product.loan_type if l.product else '',
            l.branch.name if l.branch else '',
            float(l.principal or 0),
            float(l.interest_rate or 0),
            l.tenure_days,
            l.status,
            l.disbursed_at.strftime('%Y-%m-%d') if l.disbursed_at else '',
            str(l.due_date) if l.due_date else '',
            float(l.total_paid or 0),
            float(l.balance or 0),
            float(l.penalty_amount or 0),
            l.loan_officer.full_name if l.loan_officer else '',
        ])
    return response
