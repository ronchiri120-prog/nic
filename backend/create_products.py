import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'quicklender_project.settings')
django.setup()

from apps.loans.models import LoanProduct
from decimal import Decimal

# Create BIASHARA product (Weekly)
biashara, created = LoanProduct.objects.get_or_create(
    name='BIASHARA',
    defaults={
        'loan_type': 'IWC',  # Individual Weekly Collection
        'min_amount': Decimal('3000'),
        'max_amount': Decimal('30000'),
        'interest_rate': Decimal('20'),  # Base rate for 4 weeks
        'tenure_days': 28,  # Default 4 weeks
        'penalty_rate': Decimal('0'),  # No penalties
        'first_loan_fee': Decimal('500'),
        'repeat_loan_fee': Decimal('400'),
        'rate_silver': Decimal('20'),
        'rate_gold': Decimal('20'),
        'rate_platinum': Decimal('20'),
        'rate_arrears': Decimal('20'),
        'is_active': True,
    }
)
if created:
    print(f"Created BIASHARA product: {biashara.id}")
else:
    print(f"BIASHARA product already exists: {biashara.id}")

# Create TAMBA product (Monthly)
tamba, created = LoanProduct.objects.get_or_create(
    name='TAMBA',
    defaults={
        'loan_type': 'IMC',  # Individual Monthly Collection
        'min_amount': Decimal('1000'),
        'max_amount': Decimal('100000'),
        'interest_rate': Decimal('25'),  # 25% for 30 days
        'tenure_days': 30,
        'penalty_rate': Decimal('2.5'),  # 2.5% penalty base
        'first_loan_fee': Decimal('500'),
        'repeat_loan_fee': Decimal('400'),
        'rate_silver': Decimal('25'),
        'rate_gold': Decimal('25'),
        'rate_platinum': Decimal('25'),
        'rate_arrears': Decimal('25'),
        'is_active': True,
    }
)
if created:
    print(f"Created TAMBA product: {tamba.id}")
else:
    print(f"TAMBA product already exists: {tamba.id}")

print("\nAll products created successfully!")
