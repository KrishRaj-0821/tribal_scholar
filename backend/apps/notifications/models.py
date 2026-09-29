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
