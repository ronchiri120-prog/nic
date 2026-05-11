"""Tests: Group / Chama Lending"""
import pytest
from decimal import Decimal


@pytest.fixture
def loan_group(db, branch, loan_officer, customer):
    from apps.groups.models import LoanGroup, GroupMembership
    group = LoanGroup.objects.create(
        name='Test Chama',
        branch=branch,
        loan_officer=loan_officer,
        max_members=20,
    )
    GroupMembership.objects.create(group=group, customer=customer, role='CHAIRPERSON')
    return group


@pytest.mark.django_db
class TestLoanGroups:
    def test_create_group(self, auth_client, branch):
        resp = auth_client.post('/api/v1/groups/', {
            'name':        'New Chama',
            'branch':      branch.id,
            'max_members': 15,
        }, format='json')
        assert resp.status_code == 201
        assert resp.data['group_id'].startswith('GRP-')
        assert resp.data['name'] == 'New Chama'

    def test_add_member_to_group(self, auth_client, loan_group, customer):
        from apps.customers.models import Customer
        # Create second customer
        second = Customer.objects.create(
            first_name='Second', last_name='Member',
            national_id='99999999', phone='0722000001',
            branch=loan_group.branch, loan_officer=loan_group.loan_officer,
        )
        resp = auth_client.post(f'/api/v1/groups/{loan_group.id}/members/', {
            'customer': second.id,
            'role':     'MEMBER',
            'shares':   1,
        }, format='json')
        assert resp.status_code == 201
        assert loan_group.member_count == 2

    def test_group_max_members_enforced(self, auth_client, db, branch, loan_officer, customer):
        from apps.groups.models import LoanGroup, GroupMembership
        from apps.customers.models import Customer

        # Create group with max_members=1
        small_group = LoanGroup.objects.create(
            name='Tiny Chama', branch=branch,
            loan_officer=loan_officer, max_members=1,
        )
        GroupMembership.objects.create(group=small_group, customer=customer)

        second = Customer.objects.create(
            first_name='Extra', last_name='Person',
            national_id='11110000', phone='0711000000',
            branch=branch, loan_officer=loan_officer,
        )
        resp = auth_client.post(f'/api/v1/groups/{small_group.id}/members/', {
            'customer': second.id, 'role': 'MEMBER',
        }, format='json')
        assert resp.status_code == 400
        assert 'full' in resp.data['detail'].lower()

    def test_create_group_loan(self, auth_client, loan_group, loan_product):
        resp = auth_client.post('/api/v1/groups/loans/', {
            'group':         loan_group.id,
            'product':       loan_product.id,
            'total_amount':  '150000',
            'interest_rate': '10',
            'tenure_days':   30,
        }, format='json')
        assert resp.status_code == 201
        assert resp.data['group_loan_id'].startswith('GRP-L')
        assert resp.data['status'] == 'PENDING'

    def test_approve_group_loan(self, auth_client, loan_group, loan_product):
        # Create and approve
        loan_resp = auth_client.post('/api/v1/groups/loans/', {
            'group':         loan_group.id,
            'product':       loan_product.id,
            'total_amount':  '90000',
            'interest_rate': '10',
            'tenure_days':   30,
        }, format='json')
        loan_id = loan_resp.data['id']

        approve_resp = auth_client.post(f'/api/v1/groups/loans/{loan_id}/approve/')
        assert approve_resp.status_code == 200
        assert 'approved' in approve_resp.data['detail'].lower()

    def test_list_groups(self, auth_client, loan_group):
        resp = auth_client.get('/api/v1/groups/')
        assert resp.status_code == 200
        names = [g['name'] for g in (resp.data.get('results') or resp.data)]
        assert loan_group.name in names

    def test_group_member_count(self, loan_group):
        assert loan_group.member_count == 1

    def test_disburse_creates_individual_loans(self, auth_client, loan_group, loan_product):
        from apps.groups.models import GroupMembership
        from apps.customers.models import Customer

        # Add a second member so we have 2 total
        second = Customer.objects.create(
            first_name='Wanjiku', last_name='Kamau',
            national_id='33330000', phone='0733000000',
            branch=loan_group.branch, loan_officer=loan_group.loan_officer,
        )
        GroupMembership.objects.create(group=loan_group, customer=second, role='TREASURER')

        # Create group loan
        loan_resp = auth_client.post('/api/v1/groups/loans/', {
            'group': loan_group.id, 'product': loan_product.id,
            'total_amount': '100000', 'interest_rate': '10', 'tenure_days': 30,
        }, format='json')
        loan_id = loan_resp.data['id']

        # Create shares (normally done by frontend)
        from apps.groups.models import GroupLoan, GroupLoanShare, GroupMembership as GM
        group_loan = GroupLoan.objects.get(id=loan_id)
        for membership in GroupMembership.objects.filter(group=loan_group):
            GroupLoanShare.objects.create(
                group_loan=group_loan,
                member=membership,
                amount=Decimal('50000'),
                total_due=Decimal('55000'),
            )

        # Approve then disburse
        auth_client.post(f'/api/v1/groups/loans/{loan_id}/approve/')
        disburse_resp = auth_client.post(f'/api/v1/groups/loans/{loan_id}/disburse/')
        assert disburse_resp.status_code == 200
        assert len(disburse_resp.data['loans_created']) == 2
