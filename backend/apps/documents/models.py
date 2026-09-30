import uuid
from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError, PermissionDenied
from apps.core.validators import validate_academic_year, validate_sha256_checksum


class SourceType(models.TextChoices):
    GUIDELINE = 'GUIDELINE', 'Guideline'
    AMENDMENT = 'AMENDMENT', 'Amendment'
    ADVERTISEMENT = 'ADVERTISEMENT', 'Advertisement'
    FAQ = 'FAQ', 'FAQ'
    INSTRUCTION_MANUAL = 'INSTRUCTION_MANUAL', 'Instruction Manual'
    SELECTION_CRITERIA = 'SELECTION_CRITERIA', 'Selection Criteria'
    INSTITUTE_LIST = 'INSTITUTE_LIST', 'Institute List'
    RESULT = 'RESULT', 'Result'
    OFFICIAL_WEBPAGE = 'OFFICIAL_WEBPAGE', 'Official Webpage'
    DATASET = 'DATASET', 'Dataset'


class SourceDocumentStatus(models.TextChoices):
    ACTIVE = 'ACTIVE', 'Active'
    SUPERSEDED = 'SUPERSEDED', 'Superseded'
    DEPRECATED = 'DEPRECATED', 'Deprecated'
    VERIFIED = 'VERIFIED', 'Verified Official Publication'


class SourceDocument(models.Model):
    """
    Registry of authentic government scheme guidelines, advertisements, gazette notifications,
    and reference lists. Ensures cryptographic provenance for all scheme rules and reference sets.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255, help_text="Official publication title")
    source_type = models.CharField(
        max_length=50,
        choices=SourceType.choices,
        help_text="Standard category of the official publication"
    )
    source_url = models.CharField(
        max_length=500,
        blank=True,
        help_text="Publicly accessible official URL (or archived government portal link)"
    )
    scheme = models.ForeignKey(
        'schemes.Scheme',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='source_documents',
        help_text="Associated scheme if specific to a single scheme"
    )
    academic_year = models.CharField(
        max_length=20,
        validators=[validate_academic_year],
        help_text="Academic cycle, e.g. 2025-26"
    )
    document_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date of issue/gazette publication"
    )
    retrieved_at = models.DateTimeField(
        default=timezone.now,
        help_text="Timestamp when the official document was retrieved and registered"
    )
    checksum = models.CharField(
        max_length=64,
        validators=[validate_sha256_checksum],
        help_text="SHA-256 hash of original document binary"
    )
    content_hash = models.CharField(
        max_length=64,
        validators=[validate_sha256_checksum],
        help_text="SHA-256 hash of extracted canonical text/data structure"
    )
    status = models.CharField(
        max_length=30,
        choices=SourceDocumentStatus.choices,
        default=SourceDocumentStatus.VERIFIED
    )
    supersedes_source = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='superseded_by',
        help_text="Prior document superseded by this publication"
    )
    notes = models.TextField(
        blank=True,
        help_text="Provenance notes, gazette notification number, or legal citations"
    )

    class Meta:
        ordering = ['-retrieved_at']
        indexes = [
            models.Index(fields=['academic_year', 'source_type']),
            models.Index(fields=['checksum']),
        ]

    def clean(self):
        if not self._state.adding and self.pk:
            old = SourceDocument.objects.filter(pk=self.pk).first()
            if old and old.status == SourceDocumentStatus.VERIFIED:
                if old.checksum != self.checksum:
                    raise ValidationError("Verified SourceDocument binary checksum cannot be altered silently.")
                if old.content_hash != self.content_hash:
                    raise ValidationError("Verified SourceDocument content_hash cannot be altered silently.")

    def delete(self, *args, **kwargs):
        if self.status == SourceDocumentStatus.VERIFIED:
            raise PermissionDenied(f"Verified SourceDocument '{self.title}' is immutable and cannot be deleted.")
        return super().delete(*args, **kwargs)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"[{self.academic_year}] {self.get_source_type_display()}: {self.title}"


class ApplicantDocumentType(models.TextChoices):
    CASTE_CERTIFICATE = 'CASTE_CERTIFICATE', 'ST Caste/Tribe Certificate'
    INCOME_CERTIFICATE = 'INCOME_CERTIFICATE', 'Competent Authority Income Certificate'
    ADMISSION_OFFER = 'ADMISSION_OFFER', 'Admission Offer / Enrolment Letter'
    FEE_RECEIPT = 'FEE_RECEIPT', 'Fee Receipt'
    DISABILITY_CERTIFICATE = 'DISABILITY_CERTIFICATE', 'UDID / Disability Certificate'
    PASSPORT = 'PASSPORT', 'Passport (for Overseas Scholarship)'
    ACADEMIC_TRANSCRIPT = 'ACADEMIC_TRANSCRIPT', 'Academic Transcript / Marksheet'
    OTHER = 'OTHER', 'Other Supporting Document'


class DocumentLifecycleStatus(models.TextChoices):
    INITIATED = 'INITIATED', 'Initiated'
    UPLOADING = 'UPLOADING', 'Uploading'
    UPLOADED = 'UPLOADED', 'Uploaded'
    QUARANTINED = 'QUARANTINED', 'Quarantined'
    SCANNING = 'SCANNING', 'Scanning'
    PROMOTION_PENDING = 'PROMOTION_PENDING', 'Promotion Pending'
    RECONCILIATION_REQUIRED = 'RECONCILIATION_REQUIRED', 'Reconciliation Required'
    SAFE = 'SAFE', 'Safe'
    REJECTED = 'REJECTED', 'Rejected'
    PROCESSING = 'PROCESSING', 'Processing'
    PROCESSED = 'PROCESSED', 'Processed'
    VERIFICATION_PENDING = 'VERIFICATION_PENDING', 'Verification Pending'
    VERIFIED = 'VERIFIED', 'Verified'
    REVOKED = 'REVOKED', 'Revoked'


class MalwareScanStatus(models.TextChoices):
    NOT_SCANNED = 'NOT_SCANNED', 'Not Scanned'
    SCANNING = 'SCANNING', 'Scanning'
    CLEAN = 'CLEAN', 'Clean'
    INFECTED = 'INFECTED', 'Infected'
    ERROR = 'ERROR', 'Scan Error'


class ContentValidationStatus(models.TextChoices):
    PENDING = 'PENDING', 'Pending Validation'
    VALID = 'VALID', 'Content Valid'
    INVALID = 'INVALID', 'Content Invalid / Malformed'
    ERROR = 'ERROR', 'Validation Error'


class DocumentJobType(models.TextChoices):
    SECURITY_SCAN = 'SECURITY_SCAN', 'Security Scan'
    CONTENT_VALIDATION = 'CONTENT_VALIDATION', 'Content Validation'
    OCR = 'OCR', 'Optical Character Recognition (Deferred)'
    DOCUMENT_CLASSIFICATION = 'DOCUMENT_CLASSIFICATION', 'Document Classification'
    FIELD_EXTRACTION = 'FIELD_EXTRACTION', 'Field Extraction'
    VERIFICATION = 'VERIFICATION', 'Verification'


class DocumentJobStatus(models.TextChoices):
    PENDING = 'PENDING', 'Pending'
    PROCESSING = 'PROCESSING', 'Processing'
    COMPLETED = 'COMPLETED', 'Completed'
    FAILED = 'FAILED', 'Failed (Retryable)'
    PERMANENT_FAILURE = 'PERMANENT_FAILURE', 'Permanent Failure'


class ApplicantDocument(models.Model):
    """
    Canonical document aggregate for scholarship submissions.
    Supports secure lifecycle transitions, quarantine tracking, and cryptographic integrity.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    application = models.ForeignKey(
        'applications.Application',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='documents',
        help_text="Authoritative business application owning this document"
    )
    applicant = models.ForeignKey(
        'accounts.User',
        on_delete=models.CASCADE,
        related_name='uploaded_documents'
    )
    document_type = models.CharField(
        max_length=50,
        choices=ApplicantDocumentType.choices
    )
    file = models.FileField(upload_to='applicant_docs/%Y/%m/', null=True, blank=True)
    file_name = models.CharField(max_length=255, blank=True)
    original_filename = models.CharField(max_length=255, blank=True)
    storage_key = models.CharField(max_length=500, blank=True, help_text="Quarantine or Safe storage key")
    detected_mime_type = models.CharField(max_length=100, blank=True)
    declared_mime_type = models.CharField(max_length=100, blank=True)
    file_size_bytes = models.PositiveBigIntegerField(default=0)
    checksum = models.CharField(
        max_length=64,
        blank=True,
        validators=[validate_sha256_checksum],
        help_text="SHA-256 hash of the uploaded applicant document"
    )
    sha256 = models.CharField(
        max_length=64,
        blank=True,
        db_index=True,
        help_text="Authoritative server-computed SHA-256 digest"
    )
    upload_source = models.CharField(max_length=50, default='WEB_PORTAL')
    lifecycle_status = models.CharField(
        max_length=30,
        choices=DocumentLifecycleStatus.choices,
        default=DocumentLifecycleStatus.INITIATED
    )
    malware_scan_status = models.CharField(
        max_length=30,
        choices=MalwareScanStatus.choices,
        default=MalwareScanStatus.NOT_SCANNED
    )
    malware_scan_timestamp = models.DateTimeField(null=True, blank=True)
    content_validation_status = models.CharField(
        max_length=30,
        choices=ContentValidationStatus.choices,
        default=ContentValidationStatus.PENDING
    )
    uploaded_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='uploaded_by_documents'
    )
    uploaded_at = models.DateTimeField(default=timezone.now)
    processed_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    revoked_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='revoked_applicant_documents'
    )
    revocation_reason = models.TextField(blank=True)
    rejection_reason = models.TextField(blank=True)
    metadata_json = models.JSONField(default=dict, blank=True)

    # Legacy fields maintained for backward compatibility
    ocr_extracted_text = models.TextField(blank=True)
    ocr_confidence_score = models.FloatField(
        default=0.0,
        help_text="Assistive OCR confidence score (0.0 - 1.0)"
    )
    is_verified_by_officer = models.BooleanField(
        default=False,
        help_text="Officer sign-off required for final verification"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['application', 'document_type']),
            models.Index(fields=['sha256']),
            models.Index(fields=['lifecycle_status']),
        ]

    VALID_LIFECYCLE_TRANSITIONS = {
        DocumentLifecycleStatus.INITIATED: {
            DocumentLifecycleStatus.UPLOADING,
            DocumentLifecycleStatus.REJECTED,
        },
        DocumentLifecycleStatus.UPLOADING: {
            DocumentLifecycleStatus.UPLOADED,
            DocumentLifecycleStatus.QUARANTINED,
            DocumentLifecycleStatus.REJECTED,
        },
        DocumentLifecycleStatus.UPLOADED: {
            DocumentLifecycleStatus.QUARANTINED,
            DocumentLifecycleStatus.SCANNING,
            DocumentLifecycleStatus.REJECTED,
        },
        DocumentLifecycleStatus.QUARANTINED: {
            DocumentLifecycleStatus.SCANNING,
            DocumentLifecycleStatus.REJECTED,
        },
        DocumentLifecycleStatus.SCANNING: {
            DocumentLifecycleStatus.PROMOTION_PENDING,
            DocumentLifecycleStatus.SAFE,
            DocumentLifecycleStatus.REJECTED,
            DocumentLifecycleStatus.QUARANTINED,
            DocumentLifecycleStatus.RECONCILIATION_REQUIRED,
        },
        DocumentLifecycleStatus.PROMOTION_PENDING: {
            DocumentLifecycleStatus.SAFE,
            DocumentLifecycleStatus.RECONCILIATION_REQUIRED,
            DocumentLifecycleStatus.REJECTED,
            DocumentLifecycleStatus.SCANNING,
        },
        DocumentLifecycleStatus.RECONCILIATION_REQUIRED: {
            DocumentLifecycleStatus.SCANNING,
            DocumentLifecycleStatus.SAFE,
            DocumentLifecycleStatus.REJECTED,
            DocumentLifecycleStatus.REVOKED,
        },
        DocumentLifecycleStatus.SAFE: {
            DocumentLifecycleStatus.PROCESSING,
            DocumentLifecycleStatus.QUARANTINED,
            DocumentLifecycleStatus.REVOKED,
        },
        DocumentLifecycleStatus.PROCESSING: {
            DocumentLifecycleStatus.PROCESSED,
            DocumentLifecycleStatus.REVOKED,
        },
        DocumentLifecycleStatus.PROCESSED: {
            DocumentLifecycleStatus.VERIFICATION_PENDING,
            DocumentLifecycleStatus.REVOKED,
        },
        DocumentLifecycleStatus.VERIFICATION_PENDING: {
            DocumentLifecycleStatus.VERIFIED,
            DocumentLifecycleStatus.REJECTED,
            DocumentLifecycleStatus.REVOKED,
        },
        DocumentLifecycleStatus.VERIFIED: {
            DocumentLifecycleStatus.REVOKED,
        },
        DocumentLifecycleStatus.REJECTED: {
            DocumentLifecycleStatus.QUARANTINED,
            DocumentLifecycleStatus.REVOKED,
        },
        DocumentLifecycleStatus.REVOKED: set(),
    }

    def clean(self):
        super().clean()
        if not self._state.adding and self.pk:
            old = ApplicantDocument.objects.filter(pk=self.pk).values('lifecycle_status').first()
            if old:
                old_status = old['lifecycle_status']
                if old_status != self.lifecycle_status:
                    # Requirement 11: SAFE -> REJECTED is forbidden unless explicit revocation
                    if old_status == DocumentLifecycleStatus.SAFE and self.lifecycle_status == DocumentLifecycleStatus.REJECTED:
                        raise ValidationError(
                            "Invalid lifecycle transition: A document cannot transition directly from 'SAFE' to 'REJECTED'. "
                            "Revocation must be used for already verified safe documents."
                        )

                    # Rule: A document must never jump directly UPLOADED/QUARANTINED -> VERIFIED
                    if old_status in (
                        DocumentLifecycleStatus.INITIATED,
                        DocumentLifecycleStatus.UPLOADING,
                        DocumentLifecycleStatus.UPLOADED,
                        DocumentLifecycleStatus.QUARANTINED,
                        DocumentLifecycleStatus.SCANNING,
                    ) and self.lifecycle_status == DocumentLifecycleStatus.VERIFIED:
                        raise ValidationError(
                            f"Invalid transition: Cannot transition document directly from '{old_status}' to 'VERIFIED'. "
                            "Verification belongs to a later human/document-intelligence stage."
                        )

                    allowed = self.VALID_LIFECYCLE_TRANSITIONS.get(old_status, set())
                    if self.lifecycle_status not in allowed:
                        raise ValidationError(
                            f"Invalid document lifecycle transition from '{old_status}' to '{self.lifecycle_status}'."
                        )

    def save(self, *args, **kwargs):
        # Bi-directional field synchronization for backward compatibility
        if self.sha256 and not self.checksum:
            self.checksum = self.sha256
        elif self.checksum and not self.sha256:
            self.sha256 = self.checksum

        if self.original_filename and not self.file_name:
            self.file_name = self.original_filename
        elif self.file_name and not self.original_filename:
            self.original_filename = self.file_name

        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.get_document_type_display()} - {self.original_filename or self.file_name} [{self.lifecycle_status}]"


class DocumentVersion(models.Model):
    """
    Historical immutable document version.
    Allows replacing a deficient document without overwriting old evidence.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document = models.ForeignKey(
        ApplicantDocument,
        on_delete=models.CASCADE,
        related_name='versions'
    )
    version_number = models.PositiveIntegerField(default=1)
    storage_key = models.CharField(max_length=500)
    sha256 = models.CharField(max_length=64, validators=[validate_sha256_checksum])
    file_size_bytes = models.PositiveBigIntegerField(default=0)
    uploaded_at = models.DateTimeField(default=timezone.now)
    uploaded_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='uploaded_document_versions'
    )
    lifecycle_status = models.CharField(
        max_length=30,
        choices=DocumentLifecycleStatus.choices,
        default=DocumentLifecycleStatus.UPLOADED
    )
    supersedes_version = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='superseded_by_versions'
    )
    reason = models.TextField(blank=True, help_text="Reason for uploading this replacement version")

    class Meta:
        ordering = ['document', '-version_number']
        unique_together = ('document', 'version_number')

    def __str__(self):
        return f"{self.document.original_filename or self.document.file_name} v{self.version_number} [{self.sha256[:8]}]"


class DocumentManifestQuerySet(models.QuerySet):
    def update(self, **kwargs):
        raise ValidationError("DocumentManifest records are strictly immutable and cannot be updated.")

    def delete(self):
        raise ValidationError("DocumentManifest records cannot be deleted.")


class DocumentManifestManager(models.Manager.from_queryset(DocumentManifestQuerySet)):
    pass


class DocumentManifest(models.Model):
    """
    Canonical, strictly immutable evidence record for a verified safe document.
    Used by downstream OCR, extraction, and verification pipelines.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document = models.ForeignKey(
        ApplicantDocument,
        on_delete=models.PROTECT,
        related_name='manifests'
    )
    sha256 = models.CharField(max_length=64, validators=[validate_sha256_checksum])
    size_bytes = models.PositiveBigIntegerField()
    detected_mime_type = models.CharField(max_length=100)
    storage_key = models.CharField(max_length=500)
    scan_status = models.CharField(max_length=30)
    validation_status = models.CharField(max_length=30)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = DocumentManifestManager()

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self._state.adding and self.pk:
            raise ValidationError("DocumentManifest records are strictly immutable.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("DocumentManifest records cannot be deleted.")

    def __str__(self):
        return f"Manifest [{self.sha256[:8]}] for Document {self.document_id}"


class DocumentProcessingJob(models.Model):
    """
    Asynchronous processing job tracking security scans and content validations.
    OCR and field extraction remain DEFERRED / NOT_IMPLEMENTED in this foundation phase.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document = models.ForeignKey(
        ApplicantDocument,
        on_delete=models.CASCADE,
        related_name='processing_jobs'
    )
    job_type = models.CharField(
        max_length=50,
        choices=DocumentJobType.choices,
        default=DocumentJobType.SECURITY_SCAN
    )
    status = models.CharField(
        max_length=30,
        choices=DocumentJobStatus.choices,
        default=DocumentJobStatus.PENDING
    )
    attempts = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    error_code = models.CharField(max_length=100, blank=True)
    error_message = models.TextField(blank=True)
    correlation_id = models.CharField(max_length=100, blank=True, db_index=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['document', 'job_type', 'status']),
            models.Index(fields=['correlation_id']),
        ]

    def __str__(self):
        return f"Job {self.job_type} on {self.document_id} [{self.status}]"


class DocumentValidityPolicy(models.TextChoices):
    PERMANENT = 'PERMANENT', 'Permanent Validity (e.g. ST Caste Certificate)'
    ISSUE_DATE_REQUIRED = 'ISSUE_DATE_REQUIRED', 'Valid Issue Date Required'
    EXPIRY_DATE_REQUIRED = 'EXPIRY_DATE_REQUIRED', 'Explicit Future Expiry Date Required'
    ACADEMIC_YEAR_BOUND = 'ACADEMIC_YEAR_BOUND', 'Bound to Academic Year of Application'
    FINANCIAL_YEAR_BOUND = 'FINANCIAL_YEAR_BOUND', 'Bound to Current Financial Year (e.g. Income Certificate)'
    NO_EXPIRY_RULE_CONFIGURED = 'NO_EXPIRY_RULE_CONFIGURED', 'No Statutory Expiry Rule Configured (Needs Review)'


class DocumentRequirement(models.Model):
    """
    Statutory document requirement attached to a specific SchemeVersion.
    Configures validity policy and verification semantics.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    scheme_version = models.ForeignKey(
        'schemes.SchemeVersion',
        on_delete=models.CASCADE,
        related_name='document_requirements',
        help_text="Target SchemeVersion enforcing this requirement"
    )
    document_type = models.CharField(
        max_length=50,
        choices=ApplicantDocumentType.choices,
        help_text="Required applicant document type"
    )
    required = models.BooleanField(
        default=True,
        help_text="True if mandatory for eligibility evaluation"
    )
    when_required = models.CharField(
        max_length=50,
        default='APPLICATION',
        help_text="Stage at which document is required (e.g. APPLICATION, SCRUTINY, VERIFICATION)"
    )
    validity_policy = models.CharField(
        max_length=50,
        choices=DocumentValidityPolicy.choices,
        default=DocumentValidityPolicy.NO_EXPIRY_RULE_CONFIGURED,
        help_text="Configured validity policy rule"
    )
    verification_required = models.BooleanField(
        default=True,
        help_text="True if officer or digital integration verification is strictly required"
    )
    acceptable_file_types = models.JSONField(
        default=list,
        blank=True,
        help_text="Permitted file formats/MIME types, e.g. ['application/pdf', 'image/jpeg', 'image/png']"
    )
    max_size_mb = models.PositiveIntegerField(
        default=5,
        help_text="Maximum allowed upload file size in megabytes"
    )
    deficiency_code = models.CharField(
        max_length=100,
        blank=True,
        help_text="Standard deficiency code triggered if missing or invalid"
    )
    deficiency_severity = models.CharField(
        max_length=30,
        default='BLOCKING',
        help_text="Deficiency severity if document requirement fails"
    )
    source_document = models.ForeignKey(
        SourceDocument,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='document_requirements',
        help_text="Official source document establishing this document requirement"
    )
    source_excerpt = models.TextField(
        blank=True,
        help_text="Exact excerpt from official guidelines defining this requirement"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['scheme_version', 'document_type']
        unique_together = ('scheme_version', 'document_type')

    def __str__(self):
        return f"{self.scheme_version}: {self.get_document_type_display()} [{self.validity_policy}]"


class JobExecutionStatus(models.TextChoices):
    STARTED = 'STARTED', 'Started'
    RUNNING = 'RUNNING', 'Running'
    COMPLETED = 'COMPLETED', 'Completed'
    FAILED = 'FAILED', 'Failed'
    CRASHED = 'CRASHED', 'Crashed'
    RETRY = 'RETRY', 'Scheduled for Retry'


class DocumentJobExecution(models.Model):
    """
    Deterministic audit tracking for individual Celery task executions.
    Guarantees idempotency and observability across retries, worker crashes, and replays.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    job = models.ForeignKey(
        DocumentProcessingJob,
        on_delete=models.CASCADE,
        related_name='executions'
    )
    task_id = models.CharField(max_length=255, db_index=True)
    document = models.ForeignKey(
        ApplicantDocument,
        on_delete=models.CASCADE,
        related_name='job_executions'
    )
    stage = models.CharField(max_length=100, default='SECURITY_SCAN')
    execution_status = models.CharField(
        max_length=50,
        choices=JobExecutionStatus.choices,
        default=JobExecutionStatus.STARTED
    )
    started_at = models.DateTimeField(default=timezone.now)
    finished_at = models.DateTimeField(null=True, blank=True)
    worker_id = models.CharField(max_length=255, blank=True)
    correlation_id = models.CharField(max_length=100, blank=True, db_index=True)
    retry_count = models.PositiveIntegerField(default=0)
    details = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-started_at']
        indexes = [
            models.Index(fields=['task_id']),
            models.Index(fields=['document', 'stage']),
            models.Index(fields=['correlation_id']),
        ]

    def __str__(self):
        return f"Execution [{self.task_id[:8]}] - {self.stage} [{self.execution_status}]"


class QuarantineDeletionStatus(models.TextChoices):
    RETAINED = 'RETAINED', 'Retained for Security/Forensics Evidence'
    PENDING_REVIEW = 'PENDING_REVIEW', 'Pending Security Officer Review'
    PURGED = 'PURGED', 'Purged in accordance with Statutory Retention Policy'


class SecurityQuarantineRecord(models.Model):
    """
    Evidence record for security threats detected during antivirus/malware scans.
    Separates security quarantine evidence storage from business document storage.
    Enforces configurable retention before statutory deletion.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document = models.ForeignKey(
        ApplicantDocument,
        on_delete=models.CASCADE,
        related_name='quarantine_records'
    )
    detection_result = models.TextField(help_text="Detailed malware/threat signature detection message")
    scanner = models.CharField(max_length=100, help_text="Malware scanner engine that flagged the document")
    detected_at = models.DateTimeField(default=timezone.now)
    retention_until = models.DateTimeField(help_text="Mandatory retention deadline before statutory deletion")
    deletion_status = models.CharField(
        max_length=50,
        choices=QuarantineDeletionStatus.choices,
        default=QuarantineDeletionStatus.RETAINED
    )
    deleted_at = models.DateTimeField(null=True, blank=True)
    quarantine_storage_key = models.CharField(max_length=500, blank=True)

    class Meta:
        ordering = ['-detected_at']
        indexes = [
            models.Index(fields=['document', 'deletion_status']),
            models.Index(fields=['retention_until']),
        ]

    def __str__(self):
        return f"Quarantine Record [{self.id}] for Doc {self.document_id} ({self.deletion_status})"


class OCRJobStatus(models.TextChoices):
    PENDING = 'PENDING', 'Pending'
    RUNNING = 'RUNNING', 'Running'
    COMPLETED = 'COMPLETED', 'Completed'
    FAILED = 'FAILED', 'Failed'
    RETRY_PENDING = 'RETRY_PENDING', 'Retry Pending'
    CANCELLED = 'CANCELLED', 'Cancelled'


class OCRJob(models.Model):
    """
    Asynchronous OCR processing job record.
    Tracks worker execution, retry attempts, failure codes, and idempotency.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document = models.ForeignKey(
        ApplicantDocument,
        on_delete=models.CASCADE,
        related_name='ocr_jobs'
    )
    document_version = models.ForeignKey(
        DocumentVersion,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='ocr_jobs'
    )
    job_type = models.CharField(max_length=50, default='OCR_EXTRACTION')
    status = models.CharField(
        max_length=30,
        choices=OCRJobStatus.choices,
        default=OCRJobStatus.PENDING
    )
    attempts = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    failure_code = models.CharField(max_length=100, blank=True)
    failure_message = models.TextField(blank=True)
    worker_id = models.CharField(max_length=255, blank=True)
    task_id = models.CharField(max_length=255, blank=True)
    correlation_id = models.CharField(max_length=100, blank=True, db_index=True)
    idempotency_key = models.CharField(max_length=255, unique=True, db_index=True)
    engine_name = models.CharField(max_length=100, default='PaddleOCR')
    engine_version = models.CharField(max_length=50, blank=True)
    pipeline_version = models.CharField(max_length=50, default='1.0.0')
    configuration_hash = models.CharField(max_length=64, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['document', 'status']),
            models.Index(fields=['idempotency_key']),
            models.Index(fields=['correlation_id']),
        ]

    def __str__(self):
        return f"OCRJob [{self.idempotency_key}] ({self.status})"


class OCRResultQuerySet(models.QuerySet):
    def update(self, **kwargs):
        raise ValidationError("OCRResult records are strictly immutable and cannot be updated.")

    def delete(self):
        raise ValidationError("OCRResult records cannot be deleted.")


class OCRResultManager(models.Manager.from_queryset(OCRResultQuerySet)):
    pass


class OCRResult(models.Model):
    """
    Immutable post-OCR artifact preserving document-level OCR output,
    engine provenance, language metadata, and cryptographic result hash.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ocr_job = models.OneToOneField(
        OCRJob,
        on_delete=models.CASCADE,
        related_name='result'
    )
    document = models.ForeignKey(
        ApplicantDocument,
        on_delete=models.CASCADE,
        related_name='ocr_results'
    )
    document_version = models.ForeignKey(
        DocumentVersion,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='ocr_results'
    )
    page_count = models.PositiveIntegerField(default=1)
    engine_name = models.CharField(max_length=100)
    engine_version = models.CharField(max_length=50)
    pipeline_version = models.CharField(max_length=50)
    language_metadata = models.JSONField(default=dict, blank=True)
    result_hash = models.CharField(max_length=64, validators=[validate_sha256_checksum])
    full_text = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = OCRResultManager()

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['document', 'created_at']),
            models.Index(fields=['result_hash']),
        ]

    def save(self, *args, **kwargs):
        if not self._state.adding and self.pk:
            raise ValidationError("OCRResult records are strictly immutable.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("OCRResult records cannot be deleted.")

    def __str__(self):
        return f"OCRResult [{self.result_hash[:8]}] Pages={self.page_count}"


class OCRPage(models.Model):
    """
    Page-level OCR representation preserving dimensions, rotation, aggregate text,
    page-level confidence, and cryptographic hash.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ocr_result = models.ForeignKey(
        OCRResult,
        on_delete=models.CASCADE,
        related_name='pages'
    )
    page_number = models.PositiveIntegerField(help_text="1-indexed page number")
    width = models.PositiveIntegerField(help_text="Rendered width in pixels")
    height = models.PositiveIntegerField(help_text="Rendered height in pixels")
    rotation = models.IntegerField(default=0, help_text="Rotation angle (0, 90, 180, 270)")
    processing_status = models.CharField(max_length=30, default='SUCCESS')
    text_aggregate = models.TextField(blank=True)
    page_confidence = models.FloatField(default=0.0)
    page_hash = models.CharField(max_length=64, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['page_number']
        unique_together = ('ocr_result', 'page_number')

    def __str__(self):
        return f"Page {self.page_number} ({self.width}x{self.height}) Conf={self.page_confidence:.2f}"


class OCRBlock(models.Model):
    """
    Smallest granular evidence unit: single block / line of extracted text
    preserving bounding box coordinates, polygon, reading order, and confidence.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    page = models.ForeignKey(
        OCRPage,
        on_delete=models.CASCADE,
        related_name='blocks'
    )
    extracted_text = models.TextField()
    confidence = models.FloatField(default=0.0, help_text="OCR model confidence score (0.0 to 1.0)")
    bbox_x = models.FloatField(default=0.0)
    bbox_y = models.FloatField(default=0.0)
    bbox_width = models.FloatField(default=0.0)
    bbox_height = models.FloatField(default=0.0)
    polygon = models.JSONField(default=list, blank=True, help_text="4-point polygon coordinates")
    block_type = models.CharField(max_length=50, default='TEXT')
    language = models.CharField(max_length=20, default='eng')
    reading_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['page', 'reading_order']
        indexes = [
            models.Index(fields=['page', 'reading_order']),
        ]

    def __str__(self):
        snippet = (self.extracted_text[:30] + '...') if len(self.extracted_text) > 30 else self.extracted_text
        return f"Block [{self.reading_order}] '{snippet}' (Conf: {self.confidence:.2f})"


class DocumentClassificationType(models.TextChoices):
    INCOME_CERTIFICATE = 'INCOME_CERTIFICATE', 'Income Certificate'
    CASTE_CERTIFICATE = 'CASTE_CERTIFICATE', 'Caste / Tribe Certificate'
    DOMICILE_CERTIFICATE = 'DOMICILE_CERTIFICATE', 'Domicile / Residence Certificate'
    MARKSHEET = 'MARKSHEET', 'Marksheet / Academic Transcript'
    ADMISSION_LETTER = 'ADMISSION_LETTER', 'Admission Offer / Enrolment Letter'
    INSTITUTION_DOCUMENT = 'INSTITUTION_DOCUMENT', 'Institution Verification Document'
    BANK_DOCUMENT = 'BANK_DOCUMENT', 'Bank Passbook / Statement'
    IDENTITY_DOCUMENT = 'IDENTITY_DOCUMENT', 'Identity Proof (Aadhaar / Voter ID / Passport)'
    OTHER = 'OTHER', 'Other Supporting Document'
    UNKNOWN = 'UNKNOWN', 'Unknown / Unclassifiable Document'


class DocumentClassificationResult(models.Model):
    """
    Deterministic rule-based classification outcome for a processed document.
    Categorizes the document and records matching evidence without claiming ML prediction.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document = models.ForeignKey(
        ApplicantDocument,
        on_delete=models.CASCADE,
        related_name='classifications'
    )
    document_version = models.ForeignKey(
        DocumentVersion,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='classifications'
    )
    ocr_result = models.ForeignKey(
        OCRResult,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='classifications'
    )
    predicted_type = models.CharField(
        max_length=50,
        choices=DocumentClassificationType.choices,
        default=DocumentClassificationType.UNKNOWN
    )
    confidence = models.FloatField(default=0.0)
    classifier_version = models.CharField(max_length=50, default='1.0.0')
    classification_method = models.CharField(max_length=50, default='RULE_BASED')
    evidence_summary = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['document', 'predicted_type']),
        ]

    def __str__(self):
        return f"Classification [{self.predicted_type}] Conf={self.confidence:.2f}"


class ProvisionalExtractedField(models.Model):
    """
    Provisional field value extracted via deterministic OCR heuristics.
    Tied directly to source evidence chain: Application -> Document -> Version -> OCRResult -> OCRPage -> OCRBlock.
    Trust rank remains OCR_PROVISIONAL (10) and NEVER outranks APPLICANT_DECLARED (20).
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document = models.ForeignKey(
        ApplicantDocument,
        on_delete=models.CASCADE,
        related_name='extracted_fields'
    )
    document_version = models.ForeignKey(
        DocumentVersion,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='extracted_fields'
    )
    ocr_result = models.ForeignKey(
        OCRResult,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='extracted_fields'
    )
    ocr_page = models.ForeignKey(
        OCRPage,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='extracted_fields'
    )
    ocr_block = models.ForeignKey(
        OCRBlock,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='extracted_fields'
    )
    field_code = models.CharField(max_length=100, db_index=True)
    field_label = models.CharField(max_length=255, blank=True)
    raw_value = models.TextField()
    normalized_value = models.JSONField(null=True, blank=True)
    confidence = models.FloatField(default=0.0)
    trust_level = models.CharField(max_length=50, default='OCR_PROVISIONAL')
    extraction_method = models.CharField(max_length=50, default='REGEX_ANCHOR')
    pipeline_version = models.CharField(max_length=50, default='1.0.0')
    page_number = models.PositiveIntegerField(default=1)
    bounding_box = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['document', 'field_code']),
            models.Index(fields=['field_code']),
        ]

    def __str__(self):
        return f"Extracted [{self.field_code}] = '{self.raw_value}' (Conf={self.confidence:.2f})"

