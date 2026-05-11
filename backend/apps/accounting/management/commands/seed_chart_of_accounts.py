"""
Management command: python manage.py seed_chart_of_accounts
Creates the standard QuickLender Chart of Accounts.
"""
from django.core.management.base import BaseCommand
from apps.accounting.models import Account, AccountType


COA = [
    # Assets
    ("1000","Current Assets",           "ASSET",  None,   True),
    ("1010","Cash & M-Pesa Float",       "ASSET",  "1000", False),
    ("1011","Cash at Bank",              "ASSET",  "1000", False),
    ("1100","Loans Receivable (Gross)",  "ASSET",  "1000", False),
    ("1110","Interest Receivable",       "ASSET",  "1000", False),
    ("1115","Penalty Receivable",        "ASSET",  "1000", False),
    ("1200","Prepaid Expenses",          "ASSET",  "1000", False),
    ("1500","Fixed Assets (Net)",        "ASSET",  None,   False),
    # Liabilities
    ("2000","Current Liabilities",       "LIABILITY", None, True),
    ("2010","Accounts Payable",          "LIABILITY", "2000", False),
    ("2020","Accrued Interest Payable",  "LIABILITY", "2000", False),
    ("2030","Customer Deposits",         "LIABILITY", "2000", False),
    # Equity
    ("3000","Equity",                    "EQUITY", None,   True),
    ("3010","Share Capital",             "EQUITY", "3000", False),
    ("3020","Retained Earnings",         "EQUITY", "3000", False),
    # Income
    ("4000","Income",                    "INCOME", None,   True),
    ("4010","Interest Income",           "INCOME", "4000", False),
    ("4020","Fee Income",                "INCOME", "4000", False),
    ("4030","Penalty Income",            "INCOME", "4000", False),
    # Expenses
    ("5000","Operating Expenses",        "EXPENSE", None,  True),
    ("5010","Staff Salaries & Benefits", "EXPENSE", "5000", False),
    ("5020","Rent & Utilities",          "EXPENSE", "5000", False),
    ("5030","M-Pesa Transaction Costs",  "EXPENSE", "5000", False),
    ("5040","Loan Loss Provision",       "EXPENSE", "5000", False),
    ("5050","Admin & Other Expenses",    "EXPENSE", "5000", False),
    # Contra
    ("6000","Contra Accounts",           "ASSET",  None,   True),
    ("6010","Loan Loss Reserve",         "ASSET",  "6000", False),
]


class Command(BaseCommand):
    help = "Seeds the standard QuickLender Chart of Accounts"

    def handle(self, *args, **options):
        self.stdout.write("Seeding Chart of Accounts...")
        created = 0
        for code, name, acct_type, parent_code, is_control in COA:
            parent = Account.objects.filter(code=parent_code).first() if parent_code else None
            _, was_created = Account.objects.get_or_create(
                code=code,
                defaults={
                    "name":         name,
                    "account_type": acct_type,
                    "parent":       parent,
                    "is_control":   is_control,
                },
            )
            if was_created:
                created += 1
                self.stdout.write(f"  + {code}  {name}")
        self.stdout.write(self.style.SUCCESS(
            f"Done. {created} accounts created, {len(COA)-created} already existed."
        ))
