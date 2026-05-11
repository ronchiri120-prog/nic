"""CRM models for customer interactions and collections"""
from django.db import models
from django.conf import settings


class CRMInteraction(models.Model):
    """Customer Relationship Management - Customer Interactions"""
    
    class ConversationMethod(models.TextChoices):
        PHONE = 'PHONE', 'Phone Call'
        SMS = 'SMS', 'SMS'
        EMAIL = 'EMAIL', 'Email'
        VISIT = 'VISIT', 'Physical Visit'
        WHATSAPP = 'WHATSAPP', 'WhatsApp'
        OTHER = 'OTHER', 'Other'
    
    class ConversationPurpose(models.TextChoices):
        COLLECTION = 'COLLECTION', 'Collections'
        FOLLOW_UP = 'FOLLOW_UP', 'Follow Up'
        VERIFICATION = 'VERIFICATION', 'Verification'
        PAYMENT_REMINDER = 'PAYMENT_REMINDER', 'Payment Reminder'
        DEFAULT_NOTICE = 'DEFAULT_NOTICE', 'Default Notice'
        NEGOTIATION = 'NEGOTIATION', 'Negotiation'
        OTHER = 'OTHER', 'Other'
    
    class ReasonForDefault(models.TextChoices):
        FINANCIAL = 'FINANCIAL', 'Financial Difficulty'
        EMPLOYMENT = 'EMPLOYMENT', 'Job Loss/Income Issue'
        HEALTH = 'HEALTH', 'Health Emergency'
        BUSINESS = 'BUSINESS', 'Business Failure'
        DISPUTE = 'DISPUTE', 'Dispute over Loan'
        FORGOTTEN = 'FORGOTTEN', 'Forgot to Pay'
        UNREACHABLE = 'UNREACHABLE', 'Unreachable'
        OTHER = 'OTHER', 'Other'
    
    class Outcome(models.TextChoices):
        PROMISE_TO_PAY = 'PTP', 'Promise to Pay'
        PAYMENT_MADE = 'PAID', 'Payment Made'
        RESTRUCTURE_REQUEST = 'RESTRUCTURE', 'Restructure Request'
        DEFAULT_CONFIRMED = 'DEFAULT', 'Default Confirmed'
        REPOSSESSION_INITIATED = 'REPOSSESSION', 'Repossession Initiated'
        ESCALATED = 'ESCALATED', 'Escalated'
        NO_RESPONSE = 'NO_RESPONSE', 'No Response'
        OTHER = 'OTHER', 'Other'
    
    class NextStep(models.TextChoices):
        VISIT = 'VISIT', 'Physical Visit'
        REPOSSESSION = 'REPOSSESSION', 'Repossession'
        ESCALATE = 'ESCALATE', 'Escalate to Management'
        FOLLOW_UP_CALL = 'CALL', 'Follow Up Call'
        SEND_NOTICE = 'NOTICE', 'Send Legal Notice'
        CLOSE = 'CLOSE', 'Close Case'
        OTHER = 'OTHER', 'Other'
    
    # Customer information
    customer = models.ForeignKey(
        'customers.Customer',
        on_delete=models.CASCADE,
        related_name='crm_interactions'
    )
    customer_name = models.CharField(max_length=255, help_text="Customer name at time of interaction")
    customer_phone = models.CharField(max_length=20, help_text="Customer phone number")
    
    # Conversation details
    conversation_method = models.CharField(
        max_length=20,
        choices=ConversationMethod.choices,
        help_text="Method of communication"
    )
    conversation_purpose = models.CharField(
        max_length=30,
        choices=ConversationPurpose.choices,
        help_text="Purpose of the conversation"
    )
    reason_for_default = models.CharField(
        max_length=30,
        choices=ReasonForDefault.choices,
        blank=True,
        help_text="Reason for default if applicable"
    )
    
    # Outcome
    outcome = models.CharField(
        max_length=30,
        choices=Outcome.choices,
        help_text="Outcome of the interaction"
    )
    outcome_details = models.TextField(
        blank=True,
        help_text="Detailed narration of the outcome"
    )
    
    # Voice recording
    recording_file = models.FileField(
        upload_to='crm/recordings/%Y/%m/',
        blank=True,
        null=True,
        help_text="Audio recording of the conversation"
    )
    recording_transcript = models.TextField(
        blank=True,
        help_text="Transcript of the conversation"
    )
    
    # Next steps
    next_interaction_date = models.DateField(
        blank=True,
        null=True,
        help_text="Date for next scheduled interaction"
    )
    next_step = models.CharField(
        max_length=30,
        choices=NextStep.choices,
        blank=True,
        help_text="Next planned action"
    )
    
    # PTP (Promise to Pay)
    ptp_amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        blank=True,
        null=True,
        help_text="Promised payment amount"
    )
    ptp_date = models.DateField(
        blank=True,
        null=True,
        help_text="Promise to pay date"
    )
    
    # Metadata
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='crm_recordings'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Loan reference (if interaction is related to a specific loan)
    loan = models.ForeignKey(
        'loans.Loan',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='crm_interactions'
    )
    
    class Meta:
        db_table = 'crm_interactions'
        ordering = ['-created_at']
        verbose_name = 'CRM Interaction'
        verbose_name_plural = 'CRM Interactions'
    
    def __str__(self):
        return f"{self.customer_name} - {self.conversation_method} - {self.created_at.strftime('%Y-%m-%d')}"
