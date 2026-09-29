import uuid
from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError

class Application(models.Model):
    """
    Core application record connecting an applicant, a specific academic-year SchemeVersion,
    and the current workflow lifecycle state.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    application_number = models.CharField(
        max_length=64,
        unique=True,
        help_text="Official tracking number (e.g. MOTA/2025-26/NFST/0001)"
    )
    applicant = models.ForeignKey(
        'applicants.ApplicantProfile',
        on_delete=models.CASCADE,
        related_name='applications'
    )
    scheme_version = models.ForeignKey(
        'schemes.SchemeVersion',
        on_delete=models.PROTECT,
        related_name='applications'
    )
    current_state = models.ForeignKey(
        'workflow.WorkflowState',
        on_delete=models.PROTECT,
        related_name='applications'
    )
    submission_data_json = models.JSONField(
        default=dict,
        blank=True,
        help_text="Canonical applicant submitted parameters evaluated against SchemeRules"
    )
    is_synthetic = models.BooleanField(
        default=True,
        help_text="True if this is a synthetic test dossier"
    )
    revision_number = models.PositiveIntegerField(
        default=1,
        help_text="Optimistic concurrency control revision counter"
    )
    last_modified_at = models.DateTimeField(auto_now=True)
    last_modified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='modified_applications'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['application_number']),
            models.Index(fields=['scheme_version', 'current_state']),
        ]

    def get_effective_field_values(self):
        """
        Calculates the effective field values using the deterministic trust hierarchy:
        OFFICER (50) > OFFICIAL_INTEGRATION (40) > VERIFIED_DOCUMENT (30) > SYSTEM (25) > APPLICANT (20) > OCR (10)
        Returns a dict: { field_code: { 'value': ..., 'source': ..., 'confidence': ..., 'field_definition_id': ... } }
        """
        values_by_field = {}
        for val in self.field_values.select_related('field_definition').all():
            code = val.field_definition.field_code
            current = values_by_field.get(code)
            if current is None or val.trust_rank > current['trust_rank'] or (
                val.trust_rank == current['trust_rank'] and val.created_at > current['created_at']
            ):
                values_by_field[code] = {
                    'value': val.value_json,
                    'source': val.source,
                    'verification_status': getattr(val, 'verification_status', 'UNVERIFIED'),
                    'confidence': val.confidence,
                    'field_definition_id': str(val.field_definition_id),
                    'trust_rank': val.trust_rank,
                    'created_at': val.created_at,
                }
        return values_by_field

    def __str__(self):
        return f"{self.application_number} ({self.scheme_version.scheme.code} - {self.current_state.code})"


class EligibilityEvaluationQuerySet(models.QuerySet):
    """Enforce append-only / immutability for evaluation history."""
    def update(self, **kwargs):
        from django.core.exceptions import ValidationError
        raise ValidationError("EligibilityEvaluation records cannot be modified via bulk update.")

    def delete(self):
        from django.core.exceptions import ValidationError
        raise ValidationError("EligibilityEvaluation records cannot be deleted.")


class EligibilityEvaluationManager(models.Manager.from_queryset(EligibilityEvaluationQuerySet)):
    pass


class EligibilityEvaluation(models.Model):
    """
    Append-only snapshot of a deterministic eligibility evaluation run.
    Ensures full auditability, reproducibility, and immutability.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    application = models.ForeignKey(
        Application,
        on_delete=models.CASCADE,
        related_name='eligibility_evaluations'
    )
    scheme_version = models.ForeignKey(
        'schemes.SchemeVersion',
        on_delete=models.PROTECT,
        related_name='evaluations'
    )
    evaluated_at = models.DateTimeField(auto_now_add=True)
    engine_version = models.CharField(max_length=50, default='2.0.0')
    result = models.JSONField(
        default=dict,
        help_text="Standardized deterministic eligibility evaluation output dictionary"
    )
    result_hash = models.CharField(
        max_length=64,
        help_text="SHA-256 hash of canonical deterministic evaluation result"
    )

    objects = EligibilityEvaluationManager()

    class Meta:
        ordering = ['-evaluated_at']
        indexes = [
            models.Index(fields=['application', '-evaluated_at']),
            models.Index(fields=['result_hash']),
        ]

    def save(self, *args, **kwargs):
        if not self._state.adding and self.pk:
            from django.core.exceptions import ValidationError
            raise ValidationError("EligibilityEvaluation records are strictly immutable.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        from django.core.exceptions import ValidationError
        raise ValidationError("EligibilityEvaluation records cannot be deleted.")

from django.conf import settings
from django.core.exceptions import ValidationError

class FieldDataType(models.TextChoices):
    TEXT = 'TEXT', 'Text'
    NUMBER = 'NUMBER', 'Number'
    DATE = 'DATE', 'Date'
    BOOLEAN = 'BOOLEAN', 'Boolean'
    SELECT = 'SELECT', 'Select (Single Choice)'
    MULTI_SELECT = 'MULTI_SELECT', 'Multi-Select'
    CURRENCY = 'CURRENCY', 'Currency / Monetary Amount'
    INSTITUTION = 'INSTITUTION', 'Institution / University Identifier'
    COURSE = 'COURSE', 'Course / Academic Program'
    COUNTRY = 'COUNTRY', 'Country'
    FILE = 'FILE', 'File / Document Upload'
    PHONE = 'PHONE', 'Phone Number'
    EMAIL = 'EMAIL', 'Email Address'

class FieldValueVerificationStatus(models.TextChoices):
    UNVERIFIED = 'UNVERIFIED', 'Unverified'
    PROVISIONALLY_EXTRACTED = 'PROVISIONALLY_EXTRACTED', 'Provisionally Extracted'
    DOCUMENT_VERIFIED = 'DOCUMENT_VERIFIED', 'Document Verified'
    OFFICER_VERIFIED = 'OFFICER_VERIFIED', 'Officer Verified'
    OFFICIAL_VERIFIED = 'OFFICIAL_VERIFIED', 'Official Verified'

class FieldValueSource(models.TextChoices):
    OFFICER = 'OFFICER', 'Officer Verified'
    OFFICIAL_INTEGRATION = 'OFFICIAL_INTEGRATION', 'Official Integration (e.g. DigiLocker)'
    VERIFIED_DOCUMENT = 'VERIFIED_DOCUMENT', 'Verified Document Extraction'
    APPLICANT = 'APPLICANT', 'Applicant Declared'
    OCR = 'OCR', 'OCR Extraction (Provisional)'
    SYSTEM = 'SYSTEM', 'System Calculated'

SOURCE_TRUST_RANK = {
    FieldValueSource.OFFICER: 50,
    FieldValueSource.OFFICIAL_INTEGRATION: 40,
    FieldValueSource.VERIFIED_DOCUMENT: 30,
    FieldValueSource.SYSTEM: 25,
    FieldValueSource.APPLICANT: 20,
    FieldValueSource.OCR: 10,
}

class ApplicationFieldDefinition(models.Model):
    """
    Statutory application form field definition bound to a specific SchemeVersion.
    Powers fully data-driven, schema-validated applicant forms without hardcoding.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    scheme_version = models.ForeignKey(
        'schemes.SchemeVersion',
        on_delete=models.CASCADE,
        related_name='field_definitions',
        help_text="SchemeVersion governing this field definition"
    )
    field_code = models.CharField(max_length=100, help_text="Canonical field identifier (e.g. annual_family_income)")
    label = models.CharField(max_length=255, help_text="Display label shown on applicant form")
    description = models.TextField(blank=True, help_text="Guidance text / help message for applicant")
    data_type = models.CharField(max_length=50, choices=FieldDataType.choices, default=FieldDataType.TEXT)
    required = models.BooleanField(default=True, help_text="Mandatory field flag")
    applicant_visible = models.BooleanField(default=True)
    officer_visible = models.BooleanField(default=True)
    editable_until_state = models.CharField(max_length=50, default='SUBMITTED')
    validation_schema = models.JSONField(
        default=dict,
        blank=True,
        help_text="JSON schema: min, max, regex, options list, or visibility_condition"
    )
    display_order = models.IntegerField(default=0)
    section = models.CharField(max_length=50, default='GENERAL', help_text="Form section code: PERSONAL, ACADEMIC, ELIGIBILITY, INSTITUTION, etc.")
    source_document = models.ForeignKey(
        'documents.SourceDocument',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='field_definitions',
        help_text="Official source document establishing this field requirement"
    )
    source_excerpt = models.TextField(blank=True, help_text="Statutory citation justifying this field requirement")
    status = models.CharField(max_length=30, default='ACTIVE')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['scheme_version', 'section', 'display_order', 'field_code']
        unique_together = ('scheme_version', 'field_code')

    def clean(self):
        if self.status == 'ACTIVE' and not self.source_document_id:
            raise ValidationError("Active ApplicationFieldDefinition must maintain source document provenance.")

    def __str__(self):
        return f"{self.scheme_version.scheme.code} ({self.scheme_version.academic_year}) - [{self.section}] {self.field_code}"


class ApplicationFieldValue(models.Model):
    """
    Immutable historical values entered or extracted for an application field.
    Preserves multiple observations with confidence scores and source provenance.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    application = models.ForeignKey(
        Application,
        on_delete=models.CASCADE,
        related_name='field_values'
    )
    field_definition = models.ForeignKey(
        ApplicationFieldDefinition,
        on_delete=models.CASCADE,
        related_name='submitted_values'
    )
    value_json = models.JSONField(null=True, blank=True, help_text="Structured submitted value")
    source = models.CharField(
        max_length=50,
        choices=FieldValueSource.choices,
        default=FieldValueSource.APPLICANT,
        help_text="Source provenance for this value"
    )
    verification_status = models.CharField(
        max_length=50,
        choices=FieldValueVerificationStatus.choices,
        default=FieldValueVerificationStatus.UNVERIFIED,
        help_text="Verification lifecycle status"
    )
    confidence = models.FloatField(default=1.0, help_text="Extraction confidence score (0.0 to 1.0)")
    entered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='entered_field_values'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    @property
    def trust_rank(self) -> int:
        return SOURCE_TRUST_RANK.get(self.source, 0)

    def save(self, *args, **kwargs):
        if not self.pk and self.verification_status == FieldValueVerificationStatus.UNVERIFIED:
            if self.source == FieldValueSource.OCR:
                self.verification_status = FieldValueVerificationStatus.PROVISIONALLY_EXTRACTED
            elif self.source == FieldValueSource.VERIFIED_DOCUMENT:
                self.verification_status = FieldValueVerificationStatus.DOCUMENT_VERIFIED
            elif self.source == FieldValueSource.OFFICER:
                self.verification_status = FieldValueVerificationStatus.OFFICER_VERIFIED
            elif self.source == FieldValueSource.OFFICIAL_INTEGRATION:
                self.verification_status = FieldValueVerificationStatus.OFFICIAL_VERIFIED
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.application.application_number} -> {self.field_definition.field_code} = {self.value_json} [{self.source}]"


class DeficiencySeverity(models.TextChoices):
    BLOCKING = 'BLOCKING', 'Blocking Deficiency'
    WARNING = 'WARNING', 'Warning / Informational'
    CORRECTIVE = 'CORRECTIVE', 'Corrective Resubmission Required'

class DeficiencyStatus(models.TextChoices):
    OPEN = 'OPEN', 'Open'
    RESPONDED = 'RESPONDED', 'Responded by Applicant'
    UNDER_REVIEW = 'UNDER_REVIEW', 'Under Review by Scrutiny Officer'
    RESOLVED = 'RESOLVED', 'Resolved by Officer'
    WAIVED = 'WAIVED', 'Waived by Officer'

class ApplicationDeficiency(models.Model):
    """
    Formal administrative deficiency raised during scrutiny.
    Ensures non-punitive due-process workflow for applicants to rectify issues.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    application = models.ForeignKey(
        Application,
        on_delete=models.CASCADE,
        related_name='deficiencies'
    )
    deficiency_code = models.CharField(max_length=100, help_text="Categorical code (e.g. DEF_INCOME_CERT_EXPIRED)")
    field_code = models.CharField(max_length=100, blank=True)
    document_type = models.CharField(max_length=50, blank=True)
    description = models.TextField(help_text="Clear explanation of deficiency and remedy required")
    severity = models.CharField(max_length=30, choices=DeficiencySeverity.choices, default=DeficiencySeverity.BLOCKING)
    raised_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='deficiencies_raised'
    )
    raised_at = models.DateTimeField(auto_now_add=True)
    due_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=30, choices=DeficiencyStatus.choices, default=DeficiencyStatus.OPEN)
    resolution_text = models.TextField(blank=True, help_text="Applicant explanation or officer resolution justification")
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='deficiencies_resolved'
    )
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-raised_at']

    def __str__(self):
        return f"{self.application.application_number} [{self.deficiency_code} - {self.status}]"


class ImmutableSnapshotQuerySet(models.QuerySet):
    """Enforce immutability and prevent bulk updates or deletions on snapshot records."""
    def update(self, **kwargs):
        raise ValidationError("Immutable snapshot records cannot be modified via bulk update.")

    def delete(self):
        raise ValidationError("Immutable snapshot records cannot be deleted.")


class ImmutableSnapshotManager(models.Manager.from_queryset(ImmutableSnapshotQuerySet)):
    pass


class EligibilityInputSnapshot(models.Model):
    """
    Immutable dossier input snapshot taken at the exact moment of an eligibility evaluation.
    Guarantees reproducibility even if the applicant profile changes later.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    evaluation = models.OneToOneField(
        EligibilityEvaluation,
        on_delete=models.CASCADE,
        related_name='input_snapshot'
    )
    payload_json = models.JSONField(default=dict)
    payload_hash = models.CharField(max_length=64, help_text="SHA-256 hash of captured input snapshot")
    created_at = models.DateTimeField(auto_now_add=True)

    objects = ImmutableSnapshotManager()

    def save(self, *args, **kwargs):
        if not self._state.adding and self.pk:
            raise ValidationError("EligibilityInputSnapshot is strictly immutable.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("EligibilityInputSnapshot cannot be deleted.")

    def __str__(self):
        return f"Snapshot for Evaluation {self.evaluation.id} ({self.payload_hash[:8]})"


class ConflictStatus(models.TextChoices):
    OPEN = 'OPEN', 'Open'
    UNDER_REVIEW = 'UNDER_REVIEW', 'Under Review'
    RESOLVED = 'RESOLVED', 'Resolved'
    WAIVED = 'WAIVED', 'Waived'


class FieldConflict(models.Model):
    """
    Contradiction between multiple data sources (e.g. Applicant vs OCR vs Document).
    Requires officer scrutiny; material conflicts cause eligibility evaluation to return NEEDS_REVIEW.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    application = models.ForeignKey(
        Application,
        on_delete=models.CASCADE,
        related_name='conflicts'
    )
    field_code = models.CharField(max_length=100, help_text="Canonical field identifier in conflict")
    values_json = models.JSONField(default=list, help_text="List of contending values observed across sources")
    source_values = models.JSONField(default=dict, help_text="Source-keyed dictionary containing detailed observed values and confidence")
    severity = models.CharField(max_length=30, default='BLOCKING')
    status = models.CharField(max_length=30, choices=ConflictStatus.choices, default=ConflictStatus.OPEN)
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='resolved_conflicts'
    )
    resolution = models.TextField(blank=True, help_text="Officer justification and resolution explanation")
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Conflict: {self.application.application_number} -> {self.field_code} [{self.status}]"


class IdempotencyRecord(models.Model):
    """
    Guarantees that retry requests with the same Idempotency-Key return the exact same receipt
    without creating duplicate submissions, workflow transitions, or audit logs.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    key = models.CharField(max_length=255, db_index=True)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='idempotency_records'
    )
    endpoint = models.CharField(max_length=255)
    request_hash = models.CharField(max_length=64)
    response_status = models.IntegerField()
    response_body = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('key', 'actor', 'endpoint')
        indexes = [
            models.Index(fields=['key', 'actor', 'endpoint']),
        ]

    def __str__(self):
        return f"IdempotencyRecord({self.key} - {self.actor.username} - {self.endpoint})"


class ApplicationSubmissionSnapshot(models.Model):
    """
    Immutable archive of the complete application state, documents manifest, and form values
    captured at the exact transaction moment of submission.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    application = models.ForeignKey(
        Application,
        on_delete=models.CASCADE,
        related_name='submission_snapshots'
    )
    revision_number = models.PositiveIntegerField()
    submitted_at = models.DateTimeField(auto_now_add=True)
    applicant_data_json = models.JSONField(default=dict)
    form_values_json = models.JSONField(default=dict)
    document_manifest_json = models.JSONField(default=list)
    scheme_version = models.ForeignKey(
        'schemes.SchemeVersion',
        on_delete=models.PROTECT,
        related_name='submission_snapshots'
    )
    snapshot_hash = models.CharField(max_length=64, help_text="SHA-256 hash of immutable submission snapshot")

    objects = ImmutableSnapshotManager()

    class Meta:
        ordering = ['-submitted_at']

    def save(self, *args, **kwargs):
        if not self._state.adding and self.pk:
            raise ValidationError("ApplicationSubmissionSnapshot is strictly immutable.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("ApplicationSubmissionSnapshot cannot be deleted.")

    def __str__(self):
        return f"SubmissionSnapshot for {self.application.application_number} (rev {self.revision_number})"


class DuplicateDetectionMode(models.TextChoices):
    STRICT = 'STRICT', 'Strict Rejection'
    WARN = 'WARN', 'Warning'
    REVIEW = 'REVIEW', 'Route to Review'


class ApplicationUniquenessPolicy(models.Model):
    """
    Configurable scheme-level policy governing multiple applications, re-applications,
    and deduplication modes.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    scheme_version = models.OneToOneField(
        'schemes.SchemeVersion',
        on_delete=models.CASCADE,
        related_name='uniqueness_policy'
    )
    max_active_applications = models.PositiveIntegerField(default=1)
    allow_multiple_drafts = models.BooleanField(default=False)
    allow_resubmission = models.BooleanField(default=False)
    duplicate_detection_mode = models.CharField(
        max_length=30,
        choices=DuplicateDetectionMode.choices,
        default=DuplicateDetectionMode.WARN
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.scheme_version}: max={self.max_active_applications}, mode={self.duplicate_detection_mode}"
