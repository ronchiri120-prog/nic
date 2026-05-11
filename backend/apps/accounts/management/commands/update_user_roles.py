from django.core.management.base import BaseCommand
from apps.accounts.models import User

class Command(BaseCommand):
    help = 'Update users with invalid roles to valid roles'

    def handle(self, *args, **options):
        # Mapping of old roles to new roles
        role_mapping = {
            'CREDIT_OFFICER': 'IDC',
            'RO': 'BDO',
            'BA': 'BDO',
            'GM': 'RM',
            'HOP': 'OPERATIONS',
            'HOP_ASST': 'OPERATIONS',
            'BDM': 'BDO',
            'ASST_BDM': 'BDO',
            'SURGE_TEAM': 'COLLECTIONS',
            'MARKETING_MGR': 'CC_MANAGER',
            'MARKETING_ASST': 'CALL_CENTRE',
            'ACCOUNTANT': 'FINANCE',
        }

        updated_count = 0
        for old_role, new_role in role_mapping.items():
            users = User.objects.filter(role=old_role)
            count = users.update(role=new_role)
            updated_count += count
            self.stdout.write(f'Updated {count} users from {old_role} to {new_role}')

        self.stdout.write(self.style.SUCCESS(f'Successfully updated {updated_count} users'))
