import uuid
from django.db import models
from django.conf import settings
from django.utils import timezone
from django.core.exceptions import ValidationError


class VerificationItemType(models.TextChoices):
    DOCUMENT = 'DOCUMENT', 'Document OCR & Integrity'
    RULE_EVALUATION = 'RULE_EVALUATION', 'Rule / Criteria Evaluation'
    IDENTITY = 'IDENTITY', 'Identity / Demographics Match'
    INSTITUTE = 'INSTITUTE', 'Institute / Course Eligibility'


class VerificationPriority(models.TextChoices):
    LOW = 'LOW', 'Low'
    NORMAL = 'NORMAL', 'Normal'
    HIGH = 'HIGH', 'High'
    URGENT = 'URGENT', 'Urgent'


class VerificationStatus(models.TextChoices):
    PENDING = 'PENDING', 'Pending Human Review'
    IN_REVIEW = 'IN_REVIEW', 'Under Officer Review'
    VERIFIED = 'VERIFIED', 'Officer Verified'
    REJECTED = 'REJECTED', 'Officer Rejected'
    NEEDS_MORE_EVIDENCE = 'NEEDS_MORE_EVIDENCE', 'Needs More Evidence'
    ESCALATED = 'ESCALATED', 'Escalated to Senior Authority'
    CLOSED = 'CLOSED', 'Closed'
    # Backward-compatible choices
    APPROVED = 'APPROVED', 'Officer Verified & Approved'
    DEFECT_FLAGGED = 'DEFECT_FLAGGED', 'Defect Identified'


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
    document = models.ForeignKey(
        'documents.ApplicantDocument',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='verification_items',
        help_text="Direct link to supporting applicant document under scrutiny"
    )
    item_type = models.CharField(max_length=40, choices=VerificationItemType.choices)
    target_identifier = models.CharField(max_length=150, help_text="Rule code or document reference")
    conflict_type = models.CharField(
        max_length=50,
        blank=True,
        default="",
        db_index=True,
        help_text="e.g. MATERIAL_CONFLICT, DATA_MISMATCH, UNREADABLE_SCAN"
    )
    priority = models.CharField(
        max_length=20,
        choices=VerificationPriority.choices,
        default=VerificationPriority.NORMAL,
        db_index=True
    )
    confidence_score = models.FloatField(
        default=1.0,
        help_text="Confidence output from AI OCR or extraction (0.0 - 1.0)"
    )
    status = models.CharField(
        max_length=30,
        choices=VerificationStatus.choices,
        default=VerificationStatus.PENDING,
        db_index=True
    )
    current_evidence_json = models.JSONField(
        default=dict,
        blank=True,
        help_text="Snapshot of declared vs OCR vs official values and respective trust ranks"
    )
    ai_assistance_json = models.JSONField(
        default=dict,
        blank=True,
        help_text="Extracted text snippets, bounding boxes, or anomaly explanations from AI"
    )
    officer_remarks = models.TextField(blank=True, help_text="Statutory notes entered by verifying officer")
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_verification_items'
    )
    assigned_at = models.DateTimeField(null=True, blank=True)
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
        ordering = ['priority', 'status', 'created_at']
        indexes = [
            models.Index(fields=['status', 'priority']),
            models.Index(fields=['assigned_to', 'status']),
            models.Index(fields=['conflict_type']),
        ]

    def __str__(self):
        return f"Review [{self.item_type}] for App {self.application.application_number} ({self.status})"


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
    NEEDS_MORE_EVIDENCE = 'NEEDS_MORE_EVIDENCE', 'Needs More Evidence'
    ESCALATE = 'ESCALATE', 'Escalate to Senior Officer'
    NEEDS_REVIEW = 'NEEDS_REVIEW', 'Flag for Senior Review'
    NO_CONFLICT = 'NO_CONFLICT', 'Direct Field Verification (No Conflict)'
    VERIFIED_DOCUMENT = 'VERIFIED_DOCUMENT', 'Verified Supporting Document Evidence'


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
    previous_source = models.CharField(
        max_length=50,
        blank=True,
        default="",
        help_text="e.g. APPLICANT_DECLARED, OCR_PROVISIONAL"
    )
    previous_trust_rank = models.IntegerField(default=10)
    verified_source = models.CharField(
        max_length=50,
        default='OFFICER_VERIFIED',
        help_text="e.g. OFFICER_VERIFIED, VERIFIED_DOCUMENT"
    )
    verified_trust_rank = models.IntegerField(default=60)
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
    audit_event_id = models.CharField(max_length=100, blank=True, default="", db_index=True)

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
