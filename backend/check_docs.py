import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'quicklender_project.settings')
django.setup()

from apps.customers.models import Customer, KYCDocument

# Check first customer
c = Customer.objects.first()
if c:
    print(f"Customer: {c.full_name} (UID: {c.uid})")
    print(f"Photo: {c.photo}")
    print(f"ID Front: {c.id_front}")
    print(f"ID Back: {c.id_back}")
    print(f"Guarantor ID Front: {c.guarantor_id_front}")
    print(f"Guarantor ID Back: {c.guarantor_id_back}")
    print(f"Guarantor Passport: {c.guarantor_passport}")
    print(f"\nKYC Documents count: {c.documents.count()}")
    for doc in c.documents.all():
        print(f"  - {doc.category}: {doc.filename} (S3 Key: {doc.s3_key})")
else:
    print("No customers found")

# Check all KYC documents
print(f"\nTotal KYC documents in system: {KYCDocument.objects.count()}")
for doc in KYCDocument.objects.all():
    print(f"  - {doc.customer.full_name}: {doc.category} - {doc.filename}")
