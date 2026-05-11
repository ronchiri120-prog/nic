"""
QuickLender — Pytest configuration & shared fixtures
"""
import pytest
from django.test import TestCase
from rest_framework.test import APIClient


@pytest.fixture(scope='session')
def django_db_setup():
    """Use test database."""
    pass


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def admin_user(db):
    from apps.accounts.models import User
    from apps.branches.models import Branch, Region

    region = Region.objects.create(name='Nairobi', code='NBI')
    branch = Branch.objects.create(name='HQ', code='HQ', region=region, disb_target=2000000)
    user = User.objects.create_user(
        email='admin@test.co.ke',
        password='TestPass@2026',
        full_name='Test Admin',
        role=User.Role.SUPER_ADMIN,
        branch=branch,
    )
    return user


@pytest.fixture
def auth_client(api_client, admin_user):
    """API client pre-authenticated as admin."""
    resp = api_client.post('/api/v1/auth/login/', {
        'email': 'admin@test.co.ke',
        'password': 'TestPass@2026',
    }, format='json')
    api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {resp.data["access"]}')
    return api_client


@pytest.fixture
def branch(db):
    from apps.branches.models import Branch, Region
    region = Region.objects.get_or_create(name='Nairobi', defaults={'code': 'NBI'})[0]
    return Branch.objects.get_or_create(name='HQ', defaults={
        'code': 'HQ', 'region': region, 'disb_target': 2000000,
    })[0]


@pytest.fixture
def loan_officer(db, branch):
    from apps.accounts.models import User
    return User.objects.create_user(
        email='lo@test.co.ke',
        password='TestPass@2026',
        full_name='Loan Officer',
        role=User.Role.LOAN_OFFICER,
        branch=branch,
    )


@pytest.fixture
def customer(db, branch, loan_officer):
    from apps.customers.models import Customer
    return Customer.objects.create(
        first_name='Test', last_name='Customer',
        national_id='12345678', phone='0712345678',
        branch=branch, loan_officer=loan_officer,
        loan_limit=200000, monthly_income=50000,
    )


@pytest.fixture
def loan_product(db):
    from apps.loans.models import LoanProduct
    from decimal import Decimal
    return LoanProduct.objects.create(
        name='Test FA',
        loan_type='FA',
        min_amount=Decimal('5000'),
        max_amount=Decimal('100000'),
        interest_rate=Decimal('10'),
        tenure_days=30,
        penalty_rate=Decimal('0.5'),
    )


@pytest.fixture
def loan(db, customer, loan_product, branch, loan_officer):
    from apps.loans.models import Loan
    from decimal import Decimal
    return Loan.objects.create(
        customer=customer,
        product=loan_product,
        branch=branch,
        loan_officer=loan_officer,
        principal=Decimal('50000'),
        interest_rate=Decimal('10'),
        tenure_days=30,
    )


@pytest.fixture
def loan_group(db, branch, loan_officer, customer):
    """A seeded loan group with one member."""
    from apps.groups.models import LoanGroup, GroupMembership
    group = LoanGroup.objects.create(
        name="Test Umoja Chama",
        branch=branch,
        loan_officer=loan_officer,
        max_members=20,
        status="ACTIVE",
    )
    GroupMembership.objects.create(
        group=group, customer=customer, role="CHAIRPERSON", shares=1
    )
    return group


@pytest.fixture
def gl_accounts(db):
    """Seed the chart of accounts for accounting tests."""
    from django.core.management import call_command
    call_command("seed_chart_of_accounts", verbosity=0)
