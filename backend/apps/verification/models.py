import uuid
from django.db import models
from django.conf import settings

class VerificationItemType(models.TextChoices):
    DOCUMENT = 'DOCUMENT', 'Document OCR & Integrity'
    RULE_EVALUATION = 'RULE_EVALUATION', 'Rule / Criteria Evaluation'
    IDENTITY = 'IDENTITY', 'Identity / Demographics Match'
    INSTITUTE = 'INSTITUTE', 'Institute / Course Eligibility'

class VerificationStatus(models.TextChoices):
    PENDING = 'PENDING', 'Pending Human Review'
    APPROVED = 'APPROVED', 'Officer Verified & Approved'
    DEFECT_FLAGGED = 'DEFECT_FLAGGED', 'Defect Identified (Sent back to Applicant)'
    REJECTED = 'REJECTED', 'Officer Rejected'

class VerificationQueueItem(models.Model):
    """
    Officer review queue for ambiguous or low-confidence verification tasks.
    Enforces the principle that AI may assist, but human review remains authoritative.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    application = models.ForeignKey(
        'applications.Application',
        on_delete=models.CASCADE,
        related_name='verification_items'
    )
    item_type = models.CharField(max_length=40, choices=VerificationItemType.choices)
    target_identifier = models.CharField(max_length=150, help_text="Rule code or document reference")
    confidence_score = models.FloatField(
        default=1.0,
        help_text="Confidence output from AI OCR or extraction (0.0 - 1.0)"
    )
    status = models.CharField(
        max_length=30,
        choices=VerificationStatus.choices,
        default=VerificationStatus.PENDING
    )
    ai_assistance_json = models.JSONField(
        default=dict,
        blank=True,
        help_text="Extracted text snippets, bounding boxes, or anomaly explanations from AI"
    )
    officer_remarks = models.TextField(blank=True, help_text="Statutory notes entered by verifying officer")
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='verifications_performed'
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['status', 'created_at']

    def __str__(self):
        return f"Review [{self.item_type}] for App {self.application.application_number} ({self.status})"
