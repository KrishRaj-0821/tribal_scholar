import uuid
from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError

class AuditAction(models.TextChoices):
    CREATE = 'CREATE', 'Create Entity'
    UPDATE = 'UPDATE', 'Update Entity'
    DELETE = 'DELETE', 'Delete Entity'
    TRANSITION = 'TRANSITION', 'Workflow Transition'
    ACCESS = 'ACCESS', 'Sensitive Data Access'
    VALIDATE = 'VALIDATE', 'Rule / System Validation'
    ELIGIBILITY_EVALUATED = 'ELIGIBILITY_EVALUATED', 'Eligibility Evaluated'
    APPLICATION_CREATED = 'APPLICATION_CREATED', 'Application Created'
    APPLICATION_SUBMITTED = 'APPLICATION_SUBMITTED', 'Application Submitted'
    SNAPSHOT_VIEWED = 'SNAPSHOT_VIEWED', 'Sensitive Snapshot Viewed'
    CONFLICT_DETECTED = 'CONFLICT_DETECTED', 'Field Value Conflict Detected'
    CONFLICT_RESOLVED = 'CONFLICT_RESOLVED', 'Field Value Conflict Resolved'
    DUPLICATE_FLAGGED = 'DUPLICATE_FLAGGED', 'Possible Duplicate Application Flagged'
    FIELD_VALUE_CHANGED = 'FIELD_VALUE_CHANGED', 'Field Value Changed'
    DOCUMENT_ADDED = 'DOCUMENT_ADDED', 'Document Added'
    DOCUMENT_UPLOAD_INITIATED = 'DOCUMENT_UPLOAD_INITIATED', 'Document Upload Initiated'
    DOCUMENT_UPLOADED = 'DOCUMENT_UPLOADED', 'Document Uploaded'
    DOCUMENT_HASHED = 'DOCUMENT_HASHED', 'Document Cryptographically Hashed'
    DOCUMENT_SCAN_STARTED = 'DOCUMENT_SCAN_STARTED', 'Document Malware Scan Started'
    DOCUMENT_SCAN_COMPLETED = 'DOCUMENT_SCAN_COMPLETED', 'Document Malware Scan Completed'
    DOCUMENT_REJECTED = 'DOCUMENT_REJECTED', 'Document Rejected by Security Engine'
    DOCUMENT_PROMOTED = 'DOCUMENT_PROMOTED', 'Document Promoted to Safe Storage'
    DOCUMENT_VIEWED = 'DOCUMENT_VIEWED', 'Document Viewed or Streamed'
    DOCUMENT_REVOKED = 'DOCUMENT_REVOKED', 'Document Revoked'
    DOCUMENT_VERSION_CREATED = 'DOCUMENT_VERSION_CREATED', 'Document Version Created'
    DEFICIENCY_RAISED = 'DEFICIENCY_RAISED', 'Deficiency Raised'
    DEFICIENCY_RESPONDED = 'DEFICIENCY_RESPONDED', 'Deficiency Responded'
    DEFICIENCY_RESOLVED = 'DEFICIENCY_RESOLVED', 'Deficiency Resolved'
    OCR_JOB_CREATED = 'OCR_JOB_CREATED', 'OCR Job Created'
    OCR_STARTED = 'OCR_STARTED', 'OCR Processing Started'
    OCR_COMPLETED = 'OCR_COMPLETED', 'OCR Processing Completed'
    OCR_FAILED = 'OCR_FAILED', 'OCR Processing Failed'
    OCR_RETRIED = 'OCR_RETRIED', 'OCR Processing Retried'
    DOCUMENT_CLASSIFIED = 'DOCUMENT_CLASSIFIED', 'Document Classified'
    FIELD_EXTRACTED = 'FIELD_EXTRACTED', 'Provisional Field Extracted'
    FIELD_CONFLICT_DETECTED = 'FIELD_CONFLICT_DETECTED', 'Field Conflict Detected'
    DOCUMENT_VERIFICATION_STARTED = 'DOCUMENT_VERIFICATION_STARTED', 'Document Verification Started'
    DOCUMENT_EVIDENCE_VERIFIED = 'DOCUMENT_EVIDENCE_VERIFIED', 'Document Evidence Verified by Officer'
    FIELD_VERIFIED = 'FIELD_VERIFIED', 'Field Verified by Officer'
    FIELD_REJECTED = 'FIELD_REJECTED', 'Field Rejected by Officer'
    FIELD_CONFLICT_RESOLVED = 'FIELD_CONFLICT_RESOLVED', 'Field Conflict Resolved by Officer'
    DOCUMENT_VERIFICATION_COMPLETED = 'DOCUMENT_VERIFICATION_COMPLETED', 'Document Verification Completed'
    DOCUMENT_VERIFICATION_REOPENED = 'DOCUMENT_VERIFICATION_REOPENED', 'Document Verification Reopened'
    VERIFICATION_ASSIGNED = 'VERIFICATION_ASSIGNED', 'Verification Queue Item Assigned'
    VERIFICATION_ESCALATED = 'VERIFICATION_ESCALATED', 'Verification Queue Item Escalated'

class AuditQuerySet(models.QuerySet):
    """Prevent bulk modifications or deletions on audit records."""
    def update(self, **kwargs):
        raise ValidationError("AuditLog records cannot be modified via bulk update.")

    def delete(self):
        raise ValidationError("AuditLog records cannot be deleted.")

class AuditManager(models.Manager.from_queryset(AuditQuerySet)):
    pass

class AuditLog(models.Model):
    """
    Append-only statutory audit trail.
    Ensures that every configuration mutation, workflow transition,
    and eligibility assessment is permanently recorded.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_actions'
    )
    actor_role = models.CharField(max_length=50, blank=True, help_text="Role at time of action")
    entity_type = models.CharField(max_length=100, help_text="Model class or domain aggregate (e.g. SchemeRule)")
    entity_id = models.CharField(max_length=100, help_text="Primary key identifier of targeted entity")
    action = models.CharField(max_length=50, choices=AuditAction.choices)
    before_json = models.JSONField(null=True, blank=True, help_text="State snapshot before mutation")
    after_json = models.JSONField(null=True, blank=True, help_text="State snapshot after mutation")
    reason = models.TextField(blank=True, help_text="Justification provided by actor")
    ip_address = models.GenericIPAddressField(null=True, blank=True, help_text="Client IP address")
    created_at = models.DateTimeField(auto_now_add=True)

    objects = AuditManager()

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['entity_type', 'entity_id']),
            models.Index(fields=['created_at']),
            models.Index(fields=['actor']),
        ]

    def save(self, *args, **kwargs):
        if not self._state.adding and self.pk:
            raise ValidationError("AuditLog records are strictly immutable and append-only.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("AuditLog records cannot be deleted.")

    def __str__(self):
        return f"[{self.created_at}] {self.action} on {self.entity_type} ({self.entity_id}) by {self.actor or 'System'}"
