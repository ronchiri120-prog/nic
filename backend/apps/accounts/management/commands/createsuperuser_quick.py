"""
Quick non-interactive superuser creation for development.
Usage: python manage.py createsuperuser_quick

Creates: admin@quicklender.co.ke / QuickLender@2026
Safe to run multiple times — skips if user already exists.
"""
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Create default dev admin (admin@quicklender.co.ke / QuickLender@2026)'

    def handle(self, *args, **options):
        from apps.accounts.models import User

        email    = 'admin@quicklender.co.ke'
        password = 'QuickLender@2026'
        name     = 'System Admin'

        if User.objects.filter(email__iexact=email).exists():
            user = User.objects.get(email__iexact=email)
            self.stdout.write(self.style.WARNING(
                f'User already exists: {user.email}  '
                f'(Staff ID: {user.staff_id})'
            ))
            return

        user = User.objects.create_superuser(
            email=email,
            password=password,
            full_name=name,
            role='SUPER_ADMIN',
        )
        self.stdout.write(self.style.SUCCESS(
            f'\n✓ Admin created\n'
            f'  Email    : {email}\n'
            f'  Password : {password}\n'
            f'  Staff ID : {user.staff_id}\n'
        ))
