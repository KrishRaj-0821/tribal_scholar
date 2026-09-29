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
    DEFICIENCY_RAISED = 'DEFICIENCY_RAISED', 'Deficiency Raised'
    DEFICIENCY_RESPONDED = 'DEFICIENCY_RESPONDED', 'Deficiency Responded'
    DEFICIENCY_RESOLVED = 'DEFICIENCY_RESOLVED', 'Deficiency Resolved'

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
    action = models.CharField(max_length=30, choices=AuditAction.choices)
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
