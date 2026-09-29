import uuid
from django.db import models
from django.core.exceptions import ValidationError
from apps.core.validators import validate_academic_year

class SchemeType(models.TextChoices):
    FELLOWSHIP = 'FELLOWSHIP', 'Higher Education Fellowship'
    SCHOLARSHIP = 'SCHOLARSHIP', 'National Scholarship'
    OVERSEAS = 'OVERSEAS', 'Overseas Scholarship/Fellowship'

class Scheme(models.Model):
    """
    Top-level Scheme definition for MoTA programs (e.g., NFST, NOS, TOP_CLASS).
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=50, unique=True, help_text="Unique scheme code (e.g. NFST, NOS, TOP_CLASS)")
    name = models.CharField(max_length=255, help_text="Official name of the scholarship/fellowship")
    description = models.TextField(help_text="Detailed objective and scope")
    ministry = models.CharField(max_length=150, default="Ministry of Tribal Affairs")
    scheme_type = models.CharField(max_length=50, choices=SchemeType.choices, default=SchemeType.SCHOLARSHIP)
    active = models.BooleanField(default=True, help_text="Master active switch for the scheme")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['code']

    def __str__(self):
        return f"{self.code} - {self.name}"


class SchemeVersionStatus(models.TextChoices):
    DRAFT = 'DRAFT', 'Draft / Under Revision'
    APPROVED = 'APPROVED', 'Officially Approved'
    ACTIVE = 'ACTIVE', 'Active for Applications'
    ARCHIVED = 'ARCHIVED', 'Archived / Concluded'
    SUPERSEDED = 'SUPERSEDED', 'Superseded by Newer Version'

class SchemeVersion(models.Model):
    """
    Scheme Version bound to a specific academic year. Enables multi-year coexistence
    without altering historical eligibility configurations.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    scheme = models.ForeignKey(Scheme, on_delete=models.CASCADE, related_name='versions')
    academic_year = models.CharField(
        max_length=20,
        validators=[validate_academic_year],
        help_text="Academic year formatted as YYYY-YY (e.g., 2025-26)"
    )
    version_number = models.PositiveIntegerField(default=1, help_text="Sequential version within the academic year")
    status = models.CharField(
        max_length=30,
        choices=SchemeVersionStatus.choices,
        default=SchemeVersionStatus.DRAFT
    )
    effective_from = models.DateField(null=True, blank=True)
    effective_to = models.DateField(null=True, blank=True)
    source_document = models.ForeignKey(
        'documents.SourceDocument',
        on_delete=models.PROTECT,
        related_name='scheme_versions',
        help_text="Official guideline, notification or advertisement authorizing this scheme version"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    approved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['scheme', '-academic_year', '-version_number']
        unique_together = ('scheme', 'academic_year', 'version_number')

    def clean(self):
        if not self.academic_year:
            raise ValidationError("A SchemeVersion must specify an academic_year.")
        if not self.source_document_id:
            raise ValidationError("A SchemeVersion must be linked to an authentic source document.")
        if not self._state.adding and self.pk:
            old = SchemeVersion.objects.filter(pk=self.pk).first()
            if old and old.status in (SchemeVersionStatus.ACTIVE, SchemeVersionStatus.ARCHIVED, SchemeVersionStatus.SUPERSEDED):
                if old.academic_year != self.academic_year:
                    raise ValidationError("SchemeVersion academic_year is immutable once active or published.")
                if old.scheme_id != self.scheme_id:
                    raise ValidationError("SchemeVersion scheme is immutable once active or published.")
                if old.version_number != self.version_number:
                    raise ValidationError("SchemeVersion version_number is immutable once active or published.")
                if old.source_document_id != self.source_document_id:
                    raise ValidationError("SchemeVersion source_document is immutable once active or published.")

    def delete(self, *args, **kwargs):
        if self.status in (SchemeVersionStatus.ACTIVE, SchemeVersionStatus.ARCHIVED, SchemeVersionStatus.SUPERSEDED):
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied(f"Published or historical SchemeVersion '{self}' is immutable and cannot be deleted.")
        return super().delete(*args, **kwargs)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.scheme.code} ({self.academic_year} v{self.version_number}) [{self.get_status_display()}]"


class DatasetStatus(models.TextChoices):
    SAMPLE = 'SAMPLE', 'Representative Sample (Incomplete)'
    PARTIAL = 'PARTIAL', 'Partial Dataset (Work In Progress)'
    COMPLETE = 'COMPLETE', 'Complete Official Roster'
    VERIFIED = 'VERIFIED', 'Complete and Cryptographically Verified'

class ReferenceSet(models.Model):
    """
    Master dataset grouping recognized institutions, qualifying examinations, or approved courses.
    Includes completeness and coverage metadata to prevent mistaking sample sets for complete rosters.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=100, unique=True, help_text="Unique identifier (e.g., TOP_CLASS_PREMIER_INSTITUTES_SAMPLE)")
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    dataset_status = models.CharField(
        max_length=30,
        choices=DatasetStatus.choices,
        default=DatasetStatus.SAMPLE,
        help_text="Completeness status of master dataset"
    )
    record_count_expected = models.PositiveIntegerField(
        default=0,
        help_text="Total expected records from official publication (e.g. 265 for Top Class)"
    )
    record_count_loaded = models.PositiveIntegerField(
        default=0,
        help_text="Current loaded record count in this reference set"
    )
    coverage_percentage = models.FloatField(
        default=0.0,
        help_text="Coverage percentage: (loaded / expected) * 100"
    )
    source_document = models.ForeignKey(
        'documents.SourceDocument',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='reference_sets',
        help_text="Official source publication authorizing this master dataset"
    )
    verified_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['code']

    def update_counts(self):
        """Update loaded counts and coverage percentage from database."""
        actual_count = self.items.count() if self.pk else self.record_count_loaded
        self.record_count_loaded = actual_count
        if self.record_count_expected > 0:
            self.coverage_percentage = round((actual_count / self.record_count_expected) * 100, 2)
        else:
            self.coverage_percentage = 100.0 if actual_count > 0 else 0.0

    def clean(self):
        if self._state.adding:
            actual_count = self.record_count_loaded
        else:
            actual_count = self.items.count()
        if self.record_count_expected > 0 and actual_count != self.record_count_expected:
            if self.dataset_status in (DatasetStatus.COMPLETE, DatasetStatus.VERIFIED):
                raise ValidationError(
                    f"Cannot mark ReferenceSet '{self.code}' as {self.dataset_status}: "
                    f"loaded count ({actual_count}) does not match expected count ({self.record_count_expected})."
                )

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.code} [{self.get_dataset_status_display()} - {self.record_count_loaded}/{self.record_count_expected}]"


class ReferenceSetItem(models.Model):
    """
    Individual items within a ReferenceSet. Every item maintains strict provenance
    to an official government roster/source document.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    reference_set = models.ForeignKey(ReferenceSet, on_delete=models.CASCADE, related_name='items')
    external_code = models.CharField(max_length=100, help_text="External identifier such as AISHE code, NIRF rank or institute code")
    name = models.CharField(max_length=255, help_text="Full institution name, course title or item label")
    metadata_json = models.JSONField(default=dict, blank=True, help_text="Structured attributes (e.g., state, institute category, nirf_rank)")
    valid_from = models.DateField(null=True, blank=True)
    valid_to = models.DateField(null=True, blank=True)
    source_document = models.ForeignKey(
        'documents.SourceDocument',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='reference_set_items',
        help_text="Official document or gazette list proving provenance of this item"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['reference_set', 'name']
        unique_together = ('reference_set', 'external_code')

    def clean(self):
        if not self.source_document_id:
            raise ValidationError("ReferenceSetItem must maintain source document provenance.")

    def __str__(self):
        return f"{self.reference_set.code}: {self.name} [{self.external_code}]"


class EligibilityStatus(models.TextChoices):
    ELIGIBLE = 'ELIGIBLE', 'Eligible Course in this Institution'
    INELIGIBLE = 'INELIGIBLE', 'Ineligible Course'
    CONDITIONAL = 'CONDITIONAL', 'Conditional / Subject to Special Approval'

class InstitutionEligibility(models.Model):
    """
    Course-specific institutional eligibility mapping.
    Prevents coarse 'institution-only' approvals where only specific notified disciplines are funded.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    scheme_version = models.ForeignKey(SchemeVersion, on_delete=models.CASCADE, related_name='institution_eligibilities')
    institution = models.ForeignKey(ReferenceSetItem, on_delete=models.CASCADE, related_name='course_eligibilities')
    course_name = models.CharField(max_length=255, help_text="Specific course, e.g., B.Tech, MBBS, MBA, LL.B, B.Des")
    course_code = models.CharField(max_length=100, blank=True, help_text="Standard discipline/course code if available")
    eligibility_status = models.CharField(max_length=30, choices=EligibilityStatus.choices, default=EligibilityStatus.ELIGIBLE)
    source_document = models.ForeignKey(
        'documents.SourceDocument',
        on_delete=models.PROTECT,
        related_name='institution_eligibilities',
        help_text="Official roster proving course-specific eligibility"
    )
    valid_from = models.DateField(null=True, blank=True)
    valid_to = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['institution', 'course_name']
        unique_together = ('scheme_version', 'institution', 'course_name')

    def __str__(self):
        return f"{self.institution.name} -> {self.course_name}: {self.eligibility_status}"


class RuleCategory(models.TextChoices):
    ELIGIBILITY = 'ELIGIBILITY', 'Eligibility (Objective Binary Qualification)'
    DOCUMENT = 'DOCUMENT', 'Document Requirement'
    SELECTION = 'SELECTION', 'Selection / Merit Scoring'
    PREFERENCE = 'PREFERENCE', 'Preference / Prioritization Metric'
    QUOTA = 'QUOTA', 'Quota / Capacity Allocation'
    BENEFIT = 'BENEFIT', 'Benefit / Entitlement Structure'
    WORKFLOW = 'WORKFLOW', 'Workflow / Statutory Transition'
    VALIDATION = 'VALIDATION', 'System / Data Integrity Validation'

RuleType = RuleCategory  # Backward compatibility alias

class RuleOperator(models.TextChoices):
    EQUALS = 'EQUALS', 'Equals (==)'
    NOT_EQUALS = 'NOT_EQUALS', 'Not Equals (!=)'
    LESS_THAN_OR_EQUAL = 'LESS_THAN_OR_EQUAL', 'Less Than or Equal (<=)'
    GREATER_THAN_OR_EQUAL = 'GREATER_THAN_OR_EQUAL', 'Greater Than or Equal (>=)'
    IN_SET = 'IN_SET', 'In Set / In Reference Set'
    NOT_IN_SET = 'NOT_IN_SET', 'Not In Set'
    EXISTS = 'EXISTS', 'Field Exists and Non-Empty'
    PENDING_OFFICIAL_EXTRACTION = 'PENDING_OFFICIAL_EXTRACTION', 'Pending Official Extraction'

class RuleSeverity(models.TextChoices):
    BLOCKING = 'BLOCKING', 'Blocking (Ineligible if Failed)'
    WARNING = 'WARNING', 'Warning / Informational'
    MANUAL_REVIEW = 'MANUAL_REVIEW', 'Requires Human Officer Review'

class RuleStatus(models.TextChoices):
    DRAFT = 'DRAFT', 'Draft'
    ACTIVE = 'ACTIVE', 'Active'
    SUSPENDED = 'SUSPENDED', 'Suspended'
    SUPERSEDED = 'SUPERSEDED', 'Superseded'
    RETIRED = 'RETIRED', 'Retired'
    PENDING_OFFICIAL_SOURCE_EXTRACTION = 'PENDING_OFFICIAL_SOURCE_EXTRACTION', 'Pending Official Source Extraction'

class SourceClaimStatus(models.TextChoices):
    VERIFIED = 'VERIFIED', 'Verified'
    PENDING_VERIFICATION = 'PENDING_VERIFICATION', 'Pending Verification'
    UNSUPPORTED = 'UNSUPPORTED', 'Unsupported'


class ProvenanceStatus(models.TextChoices):
    OFFICIAL_VERIFIED = 'OFFICIAL_VERIFIED', 'Official Verified'
    OFFICIAL_PENDING_VERIFICATION = 'OFFICIAL_PENDING_VERIFICATION', 'Official Pending Verification'
    UNVERIFIED = 'UNVERIFIED', 'Unverified'
    UNSUPPORTED = 'UNSUPPORTED', 'Unsupported by official sources'

ProvenanceStatus.VERIFIED = ProvenanceStatus.OFFICIAL_VERIFIED
ProvenanceStatus.PENDING_VERIFICATION = ProvenanceStatus.OFFICIAL_PENDING_VERIFICATION

class SchemeRule(models.Model):
    """
    Deterministic rule definition for scheme qualification.
    Stored as configuration in the database; NEVER hardcoded in Python code.
    Explicitly classified into exactly one RuleCategory.
    """
    def __init__(self, *args, **kwargs):
        if 'rule_type' in kwargs:
            kwargs['category'] = kwargs.pop('rule_type')
        super().__init__(*args, **kwargs)

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    scheme_version = models.ForeignKey(SchemeVersion, on_delete=models.CASCADE, related_name='rules')
    rule_code = models.CharField(max_length=100, help_text="Unique rule identifier (e.g. NFST_2025_ST_COMMUNITY)")
    category = models.CharField(
        max_length=30,
        choices=RuleCategory.choices,
        default=RuleCategory.ELIGIBILITY,
        help_text="Explicit functional category of this scheme rule"
    )
    field_path = models.CharField(
        max_length=255,
        help_text="Application data path, e.g. 'applicant.community' or 'applicant.annual_family_income'"
    )
    operator = models.CharField(max_length=40, choices=RuleOperator.choices)
    value = models.JSONField(
        null=True,
        blank=True,
        help_text="Expected scalar/list value (e.g. 'ST', 600000). Null if PENDING_OFFICIAL_EXTRACTION."
    )
    reference_set = models.ForeignKey(
        ReferenceSet,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='rules',
        help_text="Reference set for IN_SET checks (e.g. list of premier institutes)"
    )
    failure_message = models.TextField(help_text="Human-readable citation displayed upon failure")
    severity = models.CharField(max_length=30, choices=RuleSeverity.choices, default=RuleSeverity.BLOCKING)
    requires_human_review = models.BooleanField(
        default=False,
        help_text="True if ambiguous/failed evaluation requires human officer scrutiny"
    )
    preference_type = models.CharField(
        max_length=50,
        blank=True,
        default="PRIORITY",
        help_text="For PREFERENCE rules: PRIORITY, RESERVATION, TIE_BREAKER"
    )
    source_document = models.ForeignKey(
        'documents.SourceDocument',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='rules',
        help_text="Exact source document proving legal provenance for this rule"
    )
    source_excerpt = models.TextField(
        blank=True,
        help_text="Short exact excerpt from the official publication justifying this rule"
    )
    confidence = models.CharField(max_length=30, default="OFFICIAL")
    status = models.CharField(
        max_length=50,
        choices=RuleStatus.choices,
        default=RuleStatus.ACTIVE,
        help_text="Lifecycle status of rule: DRAFT, ACTIVE, SUSPENDED, SUPERSEDED, RETIRED"
    )
    superseded_by_rule = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='superseded_rules',
        help_text="Replacement rule that supersedes this historical rule"
    )
    superseded_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp when this rule was superseded or retired"
    )
    superseded_reason = models.TextField(
        blank=True,
        help_text="Statutory explanation or amendment citation for superseding this rule"
    )
    provenance_status = models.CharField(
        max_length=40,
        choices=ProvenanceStatus.choices,
        default=ProvenanceStatus.OFFICIAL_VERIFIED,
        help_text="Status of legal/official provenance for this rule"
    )

    class Meta:
        ordering = ['scheme_version', 'rule_code']
        unique_together = ('scheme_version', 'rule_code')

    @property
    def rule_type(self) -> str:
        """Backward compatibility alias for category."""
        return self.category

    def clean(self):
        if not self.source_document_id:
            raise ValidationError("Every SchemeRule must be linked to a verified source_document.")

    def __str__(self):
        return f"{self.scheme_version.scheme.code} [{self.category}]: {self.rule_code}"


class QuotaGender(models.TextChoices):
    ANY = 'ANY', 'Any Gender'
    FEMALE = 'FEMALE', 'Female Only (Earmarked)'
    MALE = 'MALE', 'Male'

class SchemeQuota(models.Model):
    """
    Capacity & slot allocation definition for a scheme version.
    Separated from applicant eligibility: evaluated during selection/award stage.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    scheme_version = models.ForeignKey(SchemeVersion, on_delete=models.CASCADE, related_name='quotas')
    quota_code = models.CharField(max_length=100, help_text="e.g. NFST_2025_TOTAL_SLOTS, NOS_2025_PVTG_AWARDS")
    total_capacity = models.PositiveIntegerField(help_text="Total allocation capacity (e.g., 750 for NFST, 20 for NOS)")
    category = models.CharField(max_length=50, default="ST", help_text="Target category: ST, PVTG, ALL")
    gender = models.CharField(max_length=30, choices=QuotaGender.choices, default=QuotaGender.ANY)
    preference_group = models.CharField(max_length=50, blank=True, help_text="Sub-group: DIVYANGJAN, PVTG, NONE")
    reserved_capacity = models.PositiveIntegerField(default=0, help_text="Earmarked / reserved slots within total capacity")
    effective_from = models.DateField(null=True, blank=True)
    effective_to = models.DateField(null=True, blank=True)
    source_document = models.ForeignKey(
        'documents.SourceDocument',
        on_delete=models.PROTECT,
        related_name='quotas',
        help_text="Official publication defining this quota"
    )
    status = models.CharField(max_length=30, default="ACTIVE")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['scheme_version', 'quota_code']
        unique_together = ('scheme_version', 'quota_code')

    def __str__(self):
        return f"{self.scheme_version.scheme.code} ({self.scheme_version.academic_year}) Quota: {self.quota_code} = {self.total_capacity}"


class SelectionMethod(models.Model):
    """
    Statutory selection procedure configuration (e.g. Expert Screening Committee Interview, UGC-NET Merit).
    Separated from deterministic eligibility evaluation.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    scheme_version = models.ForeignKey(SchemeVersion, on_delete=models.CASCADE, related_name='selection_methods')
    code = models.CharField(max_length=100, help_text="e.g. EXPERT_COMMITTEE_INTERVIEW, UGC_NET_MERIT_SCORE")
    name = models.CharField(max_length=255)
    human_decision_required = models.BooleanField(
        default=True,
        help_text="Whether selection requires human expert/committee sign-off"
    )
    description = models.TextField(help_text="Detailed description of selection procedure")
    source_document = models.ForeignKey(
        'documents.SourceDocument',
        on_delete=models.PROTECT,
        related_name='selection_methods',
        help_text="Official publication authorizing this selection method"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['scheme_version', 'code']
        unique_together = ('scheme_version', 'code')

    def __str__(self):
        return f"{self.scheme_version.scheme.code} Selection: {self.name} (Human Decision: {self.human_decision_required})"
