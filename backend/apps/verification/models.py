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


from django.utils import timezone
from django.core.exceptions import ValidationError


class VerificationRecordStatus(models.TextChoices):
    PENDING = 'PENDING', 'Pending Human Review'
    VERIFIED = 'VERIFIED', 'Explicitly Verified by Officer'
    REJECTED = 'REJECTED', 'Explicitly Rejected by Officer'
    CONFLICT = 'CONFLICT', 'Material Field Conflict Flagged'
    NEEDS_REVIEW = 'NEEDS_REVIEW', 'Requires Additional Review / Inquiry'


class VerificationDecisionAction(models.TextChoices):
    USE_APPLICANT_DECLARATION = 'USE_APPLICANT_DECLARATION', 'Use Applicant Declaration'
    USE_DOCUMENT_VALUE = 'USE_DOCUMENT_VALUE', 'Use Document Evidence Value'
    REQUEST_CORRECTION = 'REQUEST_CORRECTION', 'Request Correction from Applicant'
    NEEDS_REVIEW = 'NEEDS_REVIEW', 'Flag for Senior Review'
    NO_CONFLICT = 'NO_CONFLICT', 'Direct Field Verification (No Conflict)'


class VerificationMethod(models.TextChoices):
    MANUAL_REVIEW = 'MANUAL_REVIEW', 'Manual Officer Inspection'
    CONFLICT_RESOLUTION = 'CONFLICT_RESOLUTION', 'Conflict Resolution Workflow'
    DOCUMENT_EVIDENCE = 'DOCUMENT_EVIDENCE', 'Document Evidence Verification'
    REOPENED = 'REOPENED', 'Verification Reopened'


class DocumentVerificationRecordQuerySet(models.QuerySet):
    def update(self, **kwargs):
        raise ValidationError("DocumentVerificationRecord records are strictly immutable.")

    def delete(self):
        raise ValidationError("DocumentVerificationRecord records cannot be deleted.")


class DocumentVerificationRecordManager(models.Manager.from_queryset(DocumentVerificationRecordQuerySet)):
    pass


class DocumentVerificationRecord(models.Model):
    """
    Persistent, immutable verification record capturing officer actions on document evidence.
    Converts OCR_PROVISIONAL evidence into OFFICER_VERIFIED / VERIFIED_DOCUMENT data.
    Preserves complete historical audit trail across edits, conflicts, and reopenings.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document = models.ForeignKey(
        'documents.ApplicantDocument',
        on_delete=models.CASCADE,
        related_name='verification_records'
    )
    document_version = models.ForeignKey(
        'documents.DocumentVersion',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='verification_records'
    )
    ocr_result = models.ForeignKey(
        'documents.OCRResult',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='verification_records'
    )
    ocr_page = models.ForeignKey(
        'documents.OCRPage',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='verification_records'
    )
    ocr_block = models.ForeignKey(
        'documents.OCRBlock',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='verification_records'
    )
    field_definition = models.ForeignKey(
        'applications.ApplicationFieldDefinition',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='verification_records'
    )
    field_code = models.CharField(max_length=100, db_index=True)
    previous_value_json = models.JSONField(null=True, blank=True)
    verified_value_json = models.JSONField(null=True, blank=True)
    verification_status = models.CharField(
        max_length=30,
        choices=VerificationRecordStatus.choices,
        default=VerificationRecordStatus.PENDING
    )
    decision_action = models.CharField(
        max_length=40,
        choices=VerificationDecisionAction.choices,
        default=VerificationDecisionAction.NO_CONFLICT
    )
    officer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='officer_verification_records'
    )
    officer_role = models.CharField(max_length=50, blank=True)
    verified_at = models.DateTimeField(default=timezone.now)
    reason = models.TextField(blank=True)
    verification_method = models.CharField(
        max_length=50,
        choices=VerificationMethod.choices,
        default=VerificationMethod.MANUAL_REVIEW
    )
    is_current = models.BooleanField(default=True, db_index=True)
    superseded_record = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='superseding_records'
    )
    correlation_id = models.CharField(max_length=100, blank=True, db_index=True)

    objects = DocumentVerificationRecordManager()

    class Meta:
        ordering = ['-verified_at']
        indexes = [
            models.Index(fields=['document', 'field_code', 'is_current']),
            models.Index(fields=['verification_status']),
            models.Index(fields=['officer']),
        ]

    def save(self, *args, **kwargs):
        if not self._state.adding and self.pk:
            raise ValidationError("DocumentVerificationRecord records are strictly immutable.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("DocumentVerificationRecord records cannot be deleted.")

    def __str__(self):
        return f"Verification [{self.field_code}] = {self.verified_value_json} ({self.verification_status}) by {self.officer}"

