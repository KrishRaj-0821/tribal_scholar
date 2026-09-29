import uuid
from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError

class WorkflowDefinition(models.Model):
    """
    Workflow engine configuration tied to a specific SchemeVersion.
    Dictates the state machine transitions and authorized roles.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    scheme_version = models.OneToOneField(
        'schemes.SchemeVersion',
        on_delete=models.CASCADE,
        related_name='workflow'
    )
    name = models.CharField(max_length=150)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Workflow: {self.name} ({self.scheme_version})"


class WorkflowState(models.Model):
    """
    Individual status node in the scheme application lifecycle.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workflow = models.ForeignKey(WorkflowDefinition, on_delete=models.CASCADE, related_name='states')
    code = models.CharField(max_length=50, help_text="Machine-readable code (e.g., DRAFT, UNDER_SCRUTINY, APPROVED)")
    display_name = models.CharField(max_length=100, help_text="Human-friendly label")
    sequence = models.PositiveIntegerField(help_text="Ordered sequence number for progression")
    applicant_visible = models.BooleanField(default=True, help_text="Whether applicant can see this state")
    officer_visible = models.BooleanField(default=True, help_text="Whether visible to verification officers")
    terminal = models.BooleanField(default=False, help_text="Terminal states (e.g. APPROVED, REJECTED, DISBURSED)")

    class Meta:
        ordering = ['workflow', 'sequence']
        unique_together = ('workflow', 'code')

    def __str__(self):
        return f"{self.workflow.name} -> {self.display_name} ({self.code})"


class WorkflowTransition(models.Model):
    """
    Authorized movement from one WorkflowState to another, governed by role and conditions.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workflow = models.ForeignKey(WorkflowDefinition, on_delete=models.CASCADE, related_name='transitions')
    from_state = models.ForeignKey(
        WorkflowState,
        on_delete=models.CASCADE,
        related_name='outgoing_transitions'
    )
    to_state = models.ForeignKey(
        WorkflowState,
        on_delete=models.CASCADE,
        related_name='incoming_transitions'
    )
    required_role = models.CharField(
        max_length=50,
        help_text="Role authorized to trigger this transition (e.g., APPLICANT, SCRUTINY_OFFICER, ADMIN)"
    )
    requires_reason = models.BooleanField(
        default=False,
        help_text="Mandatory textual justification for this action (e.g. defect marking or rejection)"
    )
    rule_condition_json = models.JSONField(
        default=dict,
        blank=True,
        help_text="Pre-requisite criteria evaluated prior to allowing transition"
    )

    class Meta:
        ordering = ['workflow', 'from_state__sequence']
        unique_together = ('workflow', 'from_state', 'to_state', 'required_role')

    def __str__(self):
        return f"{self.from_state.code} -> {self.to_state.code} by {self.required_role}"


class ApplicationStatusHistory(models.Model):
    """
    Append-only statutory audit trail of all application workflow state transitions.
    Modifications or deletions are strictly prohibited.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    application = models.ForeignKey(
        'applications.Application',
        on_delete=models.CASCADE,
        related_name='status_history'
    )
    from_state = models.ForeignKey(
        WorkflowState,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='+'
    )
    to_state = models.ForeignKey(
        WorkflowState,
        on_delete=models.PROTECT,
        related_name='+'
    )
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True
    )
    reason = models.TextField(blank=True, help_text="Justification or official remarks for transition")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def save(self, *args, **kwargs):
        # Enforce append-only invariant
        if not self._state.adding and self.pk:
            raise ValidationError("ApplicationStatusHistory records are immutable and append-only.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        # Prevent deletion of statutory workflow history
        raise ValidationError("ApplicationStatusHistory records cannot be deleted.")

    def __str__(self):
        return f"App {self.application_id}: {self.from_state} -> {self.to_state} at {self.created_at}"
