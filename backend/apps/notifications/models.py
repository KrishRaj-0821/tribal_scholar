import uuid
from django.db import models
from django.conf import settings


class NotificationChannel(models.TextChoices):
    PORTAL = 'PORTAL', 'In-App Portal Notification'
    SMS = 'SMS', 'SMS Alert'
    EMAIL = 'EMAIL', 'Email Notification'


class NotificationStatus(models.TextChoices):
    PENDING = 'PENDING', 'Pending Dispatch'
    SENT = 'SENT', 'Sent Successfully'
    FAILED = 'FAILED', 'Dispatch Failed'


class Notification(models.Model):
    """
    Multi-channel notification record for workflow progress,
    defect requests, and sanction notices.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    channel = models.CharField(
        max_length=20,
        choices=NotificationChannel.choices,
        default=NotificationChannel.PORTAL
    )
    title = models.CharField(max_length=255)
    message = models.TextField()
    status = models.CharField(
        max_length=20,
        choices=NotificationStatus.choices,
        default=NotificationStatus.PENDING
    )
    metadata_json = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.get_channel_display()}] {self.title} -> {self.recipient.username}"


class SMSNotificationType(models.TextChoices):
    APPLICATION_SUBMITTED = 'APPLICATION_SUBMITTED', 'Application Submitted'
    VERIFICATION_COMPLETED = 'VERIFICATION_COMPLETED', 'Verification Completed'
    NEEDS_MORE_EVIDENCE = 'NEEDS_MORE_EVIDENCE', 'Action Required / Needs More Evidence'
    APPLICATION_STATUS_CHANGED = 'APPLICATION_STATUS_CHANGED', 'Application Status Changed'
    DOCUMENT_PROCESSING_COMPLETED = 'DOCUMENT_PROCESSING_COMPLETED', 'Document Processing Completed'
    OTP = 'OTP', 'One-Time Password'


class SMSDeliveryStatus(models.TextChoices):
    PENDING = 'PENDING', 'Pending Dispatch'
    SENDING = 'SENDING', 'Sending via Provider'
    SENT = 'SENT', 'Delivered to Provider'
    FAILED = 'FAILED', 'Delivery Failed'
    RETRY_PENDING = 'RETRY_PENDING', 'Pending Retry'
    DEV_SKIPPED = 'DEV_SKIPPED', 'Skipped in Development Mode'


# Convenient aliases
NotificationType = SMSNotificationType
NotificationStatus = SMSDeliveryStatus



class SMSNotification(models.Model):
    """
    Authoritative SMS notification delivery and audit ledger.
    Never stores plaintext credentials or sensitive applicant identity.
    Enforces idempotency to prevent duplicate mobile dispatches.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    notification_type = models.CharField(
        max_length=50,
        choices=SMSNotificationType.choices,
        db_index=True
    )
    application = models.ForeignKey(
        'applications.Application',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='sms_notifications'
    )
    recipient_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sms_notifications'
    )
    recipient_phone_masked = models.CharField(
        max_length=20,
        help_text="Masked phone number (e.g. ******4912) to protect PII."
    )
    provider = models.CharField(max_length=50, default='fast2sms')
    provider_request_id = models.CharField(max_length=150, blank=True, null=True)
    status = models.CharField(
        max_length=30,
        choices=SMSDeliveryStatus.choices,
        default=SMSDeliveryStatus.PENDING,
        db_index=True
    )
    message_length = models.PositiveIntegerField(default=0)
    idempotency_key = models.CharField(
        max_length=255,
        unique=True,
        db_index=True,
        help_text="Unique key ensuring idempotency and zero duplicate SMS transmissions."
    )
    failure_reason = models.TextField(blank=True, default='')
    retry_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['application', 'notification_type']),
            models.Index(fields=['status', 'created_at']),
        ]

    def __str__(self):
        return f"SMS [{self.notification_type}] -> {self.recipient_phone_masked} ({self.status})"


class OTPVerification(models.Model):
    """
    Cryptographically secure One-Time Password verification ledger.
    Stores only salted hashes (make_password). Plaintext OTP is NEVER stored.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    phone_number = models.CharField(max_length=15, db_index=True)
    phone_masked = models.CharField(max_length=20)
    otp_hash = models.CharField(max_length=255)
    attempts = models.PositiveIntegerField(default=0)
    max_attempts = models.PositiveIntegerField(default=5)
    expires_at = models.DateTimeField()
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='otp_verifications'
    )

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['phone_number', 'is_verified', 'expires_at']),
        ]

    def __str__(self):
        return f"OTP for {self.phone_masked} (Verified: {self.is_verified})"
