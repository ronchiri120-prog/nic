"""
Management command: python manage.py setup_real_data
Creates the minimum required data to start using QuickLender with real data:
  - Super admin user (prompts for email/password)
  - Chart of accounts (GL)
  - First fiscal period (current quarter)
  - No demo customers, loans, or test data

Run this INSTEAD of seed_demo_data when going live.
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
import datetime


class Command(BaseCommand):
    help = 'Set up QuickLender for real data — creates admin user and GL accounts only'

    def handle(self, *args, **options):
        self.stdout.write('\n⚡ QuickLender — Real Data Setup\n' + '─' * 50)
        self.stdout.write('This sets up the system for live use with NO test data.\n')

        self._create_admin()
        self._seed_gl()
        self._create_fiscal_period()

        self.stdout.write('\n' + '─' * 50)
        self.stdout.write(self.style.SUCCESS(
            '✅ Setup complete!\n\n'
            'Next steps:\n'
            '  1. Log in with the admin credentials above\n'
            '  2. Go to Branches → add your regions and branches\n'
            '  3. Go to Staff → add your loan officers\n'
            '  4. Go to Settings → configure loan products and M-Pesa\n'
            '  5. Start registering customers via Reference Check → Customers\n'
        ))

    def _create_admin(self):
        from apps.accounts.models import User
        self.stdout.write('\n[1/3] Admin User')

        if User.objects.filter(is_superuser=True).exists():
            admin = User.objects.filter(is_superuser=True).first()
            self.stdout.write(self.style.WARNING(
                f'  ⚠  Superuser already exists: {admin.email}\n'
                f'  Skipping — use the existing account or create another via the admin panel.'
            ))
            return

        self.stdout.write('  Creating super admin account…')
        email    = input('  Email address: ').strip()
        name     = input('  Full name:     ').strip()
        password = input('  Password:      ').strip()

        if not email or not password or not name:
            self.stdout.write(self.style.ERROR('  ✗ All fields required. Run setup_real_data again.'))
            return

        user = User.objects.create_superuser(
            email=email,
            password=password,
            full_name=name,
            role='SUPER_ADMIN',
        )
        self.stdout.write(self.style.SUCCESS(f'  ✓ Admin created: {user.email} (Staff ID: {user.staff_id})'))

    def _seed_gl(self):
        self.stdout.write('\n[2/3] Chart of Accounts')
        try:
            from django.core.management import call_command
            call_command('seed_chart_of_accounts', verbosity=0)
            from apps.accounting.models import Account
            count = Account.objects.count()
            self.stdout.write(self.style.SUCCESS(f'  ✓ {count} GL accounts ready'))
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'  ⚠  GL setup failed: {e}'))

    def _create_fiscal_period(self):
        self.stdout.write('\n[3/3] Fiscal Period')
        try:
            from apps.accounting.models import FiscalPeriod
            today = timezone.now().date()
            # Find current quarter
            q = (today.month - 1) // 3 + 1
            q_start_month = (q - 1) * 3 + 1
            q_start = today.replace(month=q_start_month, day=1)
            q_end_month = q_start_month + 2
            if q_end_month > 12:
                q_end_month -= 12
                q_end = today.replace(year=today.year + 1, month=q_end_month, day=1)
            else:
                q_end = today.replace(month=q_end_month, day=1)
            # Last day of quarter end month
            import calendar
            last_day = calendar.monthrange(q_end.year, q_end.month)[1]
            q_end = q_end.replace(day=last_day)

            period_name = f'Q{q} {today.year}'
            period, created = FiscalPeriod.objects.get_or_create(
                name=period_name,
                defaults={'start_date': q_start, 'end_date': q_end, 'status': 'OPEN'},
            )
            status = 'created' if created else 'already exists'
            self.stdout.write(self.style.SUCCESS(
                f'  ✓ Fiscal period {period_name} {status} ({q_start} → {q_end})'
            ))
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'  ⚠  Fiscal period setup failed: {e}'))
