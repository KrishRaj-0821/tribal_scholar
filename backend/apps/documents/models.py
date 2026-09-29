import uuid
from django.db import models
from django.utils import timezone
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
        from django.core.exceptions import ValidationError
        if not self._state.adding and self.pk:
            old = SourceDocument.objects.filter(pk=self.pk).first()
            if old and old.status == SourceDocumentStatus.VERIFIED:
                if old.checksum != self.checksum:
                    raise ValidationError("Verified SourceDocument binary checksum cannot be altered silently.")
                if old.content_hash != self.content_hash:
                    raise ValidationError("Verified SourceDocument content_hash cannot be altered silently.")

    def delete(self, *args, **kwargs):
        if self.status == SourceDocumentStatus.VERIFIED:
            from django.core.exceptions import PermissionDenied
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

class ApplicantDocument(models.Model):
    """
    Foundation entity for applicant document submissions.
    Stores metadata, cryptographic checksum, and AI extraction readiness.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
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
    file_name = models.CharField(max_length=255)
    checksum = models.CharField(
        max_length=64,
        validators=[validate_sha256_checksum],
        help_text="SHA-256 hash of the uploaded applicant document"
    )
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

    def __str__(self):
        return f"{self.get_document_type_display()} - {self.file_name}"


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
