"""
Management command: python manage.py seed_demo_data
Seeds database with realistic demo data for QuickLender.
"""
from django.core.management.base import BaseCommand
from django.db import transaction


class Command(BaseCommand):
    help = "Seeds the database with QuickLender demo data"


    def add_arguments(self, parser):
        parser.add_argument(
            '--setup-only',
            action='store_true',
            help='Create only the admin user and branch structure — no demo customers or loans.',
        )

    def handle(self, *args, **options):
        self.stdout.write("Seeding QuickLender demo data...")
        with transaction.atomic():
            self._seed_regions()
            self._seed_branches()
            self._seed_users()
            self._seed_loan_products()
            self._seed_customers()
        self.stdout.write(self.style.SUCCESS("Demo data seeded successfully!"))

    def _seed_regions(self):
        from apps.branches.models import Region
        regions = [
            {"name": "Nairobi", "code": "NBI"},
            {"name": "Coast", "code": "CST"},
            {"name": "Western", "code": "WST"},
            {"name": "Rift Valley", "code": "RVL"},
        ]
        for r in regions:
            Region.objects.get_or_create(code=r["code"], defaults=r)
        self.stdout.write(f"  Created {len(regions)} regions")

    def _seed_branches(self):
        from apps.branches.models import Branch, Region
        nbi = Region.objects.get(code="NBI")
        cst = Region.objects.get(code="CST")
        wst = Region.objects.get(code="WST")
        branches = [
            {"name": "HQ — Nairobi CBD", "code": "HQ",  "region": nbi, "disb_target": 2000000},
            {"name": "Westlands",         "code": "WLD", "region": nbi, "disb_target": 1500000},
            {"name": "Mombasa Road",      "code": "MBA", "region": cst, "disb_target": 800000},
            {"name": "Kisumu",            "code": "KSM", "region": wst, "disb_target": 600000},
        ]
        for b in branches:
            Branch.objects.get_or_create(code=b["code"], defaults=b)
        self.stdout.write(f"  Created {len(branches)} branches")

    def _seed_users(self):
        from apps.accounts.models import User
        from apps.branches.models import Branch
        hq  = Branch.objects.get(code="HQ")
        wld = Branch.objects.get(code="WLD")
        users = [
            {"email": "admin@quicklender.co.ke", "full_name": "Admin Kamau", "role": User.Role.SUPER_ADMIN, "branch": hq, "password": "QuickLender@2026"},
            {"email": "james.mwangi@quicklender.co.ke", "full_name": "James Mwangi", "role": User.Role.LOAN_OFFICER, "branch": hq, "password": "Pass@2026"},
            {"email": "grace.otieno@quicklender.co.ke", "full_name": "Grace Otieno", "role": User.Role.CREDIT_OFFICER, "branch": wld, "password": "Pass@2026"},
            {"email": "jane.wangari@quicklender.co.ke", "full_name": "Jane Wangari", "role": User.Role.COLLECTIONS, "branch": hq, "password": "Pass@2026"},
            {"email": "mary.njeru@quicklender.co.ke", "full_name": "Mary Njeru", "role": User.Role.ACCOUNTANT, "branch": hq, "password": "Pass@2026"},
        ]
        for u in users:
            pw = u.pop("password")
            user, created = User.objects.get_or_create(email=u["email"], defaults=u)
            if created:
                user.set_password(pw)
                user.save()
        self.stdout.write(f"  Created {len(users)} users")

    def _seed_loan_products(self):
        from apps.loans.models import LoanProduct
        from decimal import Decimal
        products = [
            {"name": "Salary Advance (FA)", "loan_type": "FA", "min_amount": 5000, "max_amount": 100000, "interest_rate": Decimal("10"), "tenure_days": 30, "penalty_rate": Decimal("0.5")},
            {"name": "Credit Check (CC)",   "loan_type": "CC", "min_amount": 10000,"max_amount": 300000, "interest_rate": Decimal("15"), "tenure_days": 60, "penalty_rate": Decimal("1.0")},
            {"name": "Logbook Loan",        "loan_type": "LOGBOOK","min_amount": 50000,"max_amount": 2000000,"interest_rate": Decimal("5"),"tenure_days": 365,"penalty_rate": Decimal("0.5")},
            {"name": "IDC Loan",            "loan_type": "IDC","min_amount": 5000, "max_amount": 50000,  "interest_rate": Decimal("20"), "tenure_days": 30, "penalty_rate": Decimal("1.0")},
            {"name": "EDC Loan",            "loan_type": "EDC","min_amount": 5000, "max_amount": 50000,  "interest_rate": Decimal("18"), "tenure_days": 30, "penalty_rate": Decimal("1.0")},
            {"name": "Biashara 4 Weeks",    "loan_type": "IMC","min_amount": 10000,"max_amount": 500000, "interest_rate": Decimal("12"), "tenure_days": 28, "penalty_rate": Decimal("0.8")},
            {"name": "Biashara 5 Weeks",    "loan_type": "IMC","min_amount": 10000,"max_amount": 500000, "interest_rate": Decimal("12"), "tenure_days": 35, "penalty_rate": Decimal("0.8")},
            {"name": "Biashara 6 Weeks",    "loan_type": "IMC","min_amount": 10000,"max_amount": 500000, "interest_rate": Decimal("12"), "tenure_days": 42, "penalty_rate": Decimal("0.8")},
        ]
        for p in products:
            LoanProduct.objects.get_or_create(name=p["name"], defaults=p)
        self.stdout.write(f"  Created {len(products)} loan products")

    def _seed_customers(self):
        from apps.customers.models import Customer
        from apps.branches.models import Branch
        from apps.accounts.models import User
        hq  = Branch.objects.get(code="HQ")
        lo  = User.objects.filter(role="LOAN_OFFICER").first()
        customers_data = [
            {"first_name":"Alice","last_name":"Wanjiru","national_id":"12345678","phone":"0712345678","monthly_income":50000,"loan_limit":100000},
            {"first_name":"Jackson","last_name":"Muoki","national_id":"23456789","phone":"0723456789","monthly_income":80000,"loan_limit":200000},
            {"first_name":"Esther","last_name":"Njoki","national_id":"34567890","phone":"0734567890","monthly_income":60000,"loan_limit":150000},
            {"first_name":"Brian","last_name":"Omondi","national_id":"45678901","phone":"0745678901","monthly_income":40000,"loan_limit":80000},
        ]
        for c in customers_data:
            Customer.objects.get_or_create(
                national_id=c["national_id"],
                defaults={**c, "branch": hq, "loan_officer": lo}
            )
        self.stdout.write(f"  Created {len(customers_data)} customers")

        # ── Seed Chart of Accounts ────────────────────────────────────────────
        self.stdout.write('  [Accounting] Seeding Chart of Accounts…')
        try:
            from django.core.management import call_command
            call_command('seed_chart_of_accounts', verbosity=0)
            self.stdout.write(self.style.SUCCESS('  ✓ Chart of Accounts seeded'))
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'  ⚠ CoA skipped: {e}'))

        # ── Seed Fiscal Period ─────────────────────────────────────────────────
        try:
            from apps.accounting.models import FiscalPeriod
            import datetime
            today = timezone.now().date()
            FiscalPeriod.objects.get_or_create(
                name='Q1 2026',
                defaults={
                    'start_date': datetime.date(2026, 1, 1),
                    'end_date':   datetime.date(2026, 3, 31),
                    'status':     'OPEN',
                },
            )
            self.stdout.write(self.style.SUCCESS('  ✓ Fiscal period seeded'))
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'  ⚠ Fiscal period skipped: {e}'))

        # ── Seed a Loan Group ──────────────────────────────────────────────────
        try:
            from apps.groups.models import LoanGroup, GroupMembership
            group, _ = LoanGroup.objects.get_or_create(
                name='Umoja Chama',
                defaults={
                    'branch':       branches[0],
                    'loan_officer': loan_officers[0],
                    'meeting_day':  'Every Tuesday',
                    'max_members':  20,
                    'status':       'ACTIVE',
                },
            )
            # Add first 3 customers as members
            for i, c in enumerate(list(customers)[:3]):
                role = 'CHAIRPERSON' if i == 0 else 'MEMBER'
                GroupMembership.objects.get_or_create(
                    group=group, customer=c,
                    defaults={'role': role, 'shares': 1},
                )
            self.stdout.write(self.style.SUCCESS(f'  ✓ Loan group "{group.name}" seeded with {group.member_count} members'))
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'  ⚠ Group seeding skipped: {e}'))

