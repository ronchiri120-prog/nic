"""
notifications/models.py
Tracks every SMS and email sent by QuickLender.
"""
from django.db import models


class SMSLog(models.Model):
    class Status(models.TextChoices):
        PENDING  = 'PENDING',  'Pending'
        SENT     = 'SENT',     'Sent'
        FAILED   = 'FAILED',   'Failed'
        DELIVERED= 'DELIVERED','Delivered'

    class Template(models.TextChoices):
        DISBURSEMENT    = 'DISBURSEMENT',    'Loan Disbursement'
        PAYMENT_CONFIRM = 'PAYMENT_CONFIRM', 'Payment Confirmation'
        PAYMENT_REMINDER= 'PAYMENT_REMINDER','Payment Reminder'
        OVERDUE_1       = 'OVERDUE_1',       'Overdue Day 1-7'
        OVERDUE_2       = 'OVERDUE_2',       'Overdue Day 8-30'
        OVERDUE_3       = 'OVERDUE_3',       'Overdue Day 30+'
        APPROVAL        = 'APPROVAL',        'Loan Approved'
        REJECTION       = 'REJECTION',       'Loan Rejected'
        CUSTOM          = 'CUSTOM',          'Custom Message'

    recipient   = models.CharField(max_length=20)           # phone number
    customer    = models.ForeignKey('customers.Customer', on_delete=models.SET_NULL, null=True, blank=True)
    loan        = models.ForeignKey('loans.Loan', on_delete=models.SET_NULL, null=True, blank=True)
    template    = models.CharField(max_length=30, choices=Template.choices, default=Template.CUSTOM)
    message     = models.TextField()
    status      = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING)
    at_message_id   = models.CharField(max_length=80, blank=True)   # Africa's Talking message ID
    at_cost         = models.CharField(max_length=20, blank=True)   # e.g. "KES 0.8"
    failure_reason  = models.TextField(blank=True)
    sent_at     = models.DateTimeField(null=True, blank=True)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'ql_sms_logs'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.template} → {self.recipient} [{self.status}]'


class EmailLog(models.Model):
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        SENT    = 'SENT',    'Sent'
        FAILED  = 'FAILED',  'Failed'

    recipient   = models.EmailField()
    subject     = models.CharField(max_length=200)
    body_text   = models.TextField()
    status      = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    error       = models.TextField(blank=True)
    sent_at     = models.DateTimeField(null=True, blank=True)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'ql_email_logs'
        ordering = ['-created_at']
