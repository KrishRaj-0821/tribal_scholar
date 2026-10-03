from rest_framework import serializers
from apps.documents.models import ApplicantDocument, OCRPage, OCRBlock, ProvisionalExtractedField
from apps.applications.models import Application, ApplicationFieldValue, ApplicationFieldDefinition
from .models import VerificationQueueItem, DocumentVerificationRecord, VerificationStatus, VerificationPriority, VerificationDecisionAction


class OCRBlockEvidenceSerializer(serializers.ModelSerializer):
    page_number = serializers.IntegerField(source='page.page_number', read_only=True)

    class Meta:
        model = OCRBlock
        fields = [
            'id', 'page_number', 'extracted_text', 'confidence',
            'bbox_x', 'bbox_y', 'bbox_width', 'bbox_height',
            'polygon', 'block_type', 'language', 'reading_order'
        ]


class OCRPageEvidenceSerializer(serializers.ModelSerializer):
    blocks = OCRBlockEvidenceSerializer(many=True, read_only=True)

    class Meta:
        model = OCRPage
        fields = [
            'id', 'page_number', 'width', 'height', 'rotation',
            'page_confidence', 'text_aggregate', 'blocks'
        ]


class DocumentEvidenceSerializer(serializers.ModelSerializer):
    applicant_name = serializers.CharField(source='applicant.get_full_name', read_only=True)
    application_number = serializers.CharField(source='application.application_number', read_only=True)
    pages = serializers.SerializerMethodField()
    latest_ocr_text = serializers.SerializerMethodField()
    classification_summary = serializers.SerializerMethodField()
    is_verified = serializers.BooleanField(source='is_verified_by_officer', read_only=True)

    class Meta:
        model = ApplicantDocument
        fields = [
            'id', 'application', 'application_number', 'applicant_name',
            'document_type', 'original_filename', 'detected_mime_type',
            'file_size_bytes', 'lifecycle_status', 'is_verified', 'uploaded_at',
            'pages', 'latest_ocr_text', 'classification_summary'
        ]

    def get_pages(self, obj):
        latest_res = obj.ocr_results.order_by('-created_at').first()
        if not latest_res:
            return []
        pages = latest_res.pages.prefetch_related('blocks').order_by('page_number')
        return OCRPageEvidenceSerializer(pages, many=True).data

    def get_latest_ocr_text(self, obj):
        latest_res = obj.ocr_results.order_by('-created_at').first()
        return latest_res.full_text if latest_res else ""

    def get_classification_summary(self, obj):
        latest_class = obj.classifications.order_by('-created_at').first()
        if not latest_class:
            return None
        return {
            "predicted_type": latest_class.predicted_type,
            "confidence": latest_class.confidence,
            "evidence_summary": latest_class.evidence_summary
        }


class OCRFieldEvidenceSerializer(serializers.Serializer):
    field_code = serializers.CharField()
    field_label = serializers.CharField()
    declared_value = serializers.JSONField(allow_null=True)
    ocr_value = serializers.JSONField(allow_null=True)
    verified_value = serializers.JSONField(allow_null=True)
    verification_status = serializers.CharField()
    confidence = serializers.FloatField()
    page_number = serializers.IntegerField(allow_null=True)
    bbox = serializers.DictField(allow_null=True)
    polygon = serializers.ListField(allow_null=True)
    ocr_block_id = serializers.CharField(allow_null=True)
    has_conflict = serializers.BooleanField()


class DocumentVerificationRecordSerializer(serializers.ModelSerializer):
    officer_name = serializers.CharField(source='officer.username', read_only=True)

    class Meta:
        model = DocumentVerificationRecord
        fields = [
            'id', 'document', 'document_version', 'field_code',
            'previous_value_json', 'verified_value_json',
            'previous_source', 'previous_trust_rank',
            'verified_source', 'verified_trust_rank',
            'verification_status', 'decision_action',
            'officer', 'officer_name', 'officer_role', 'verified_at',
            'reason', 'verification_method', 'is_current', 'correlation_id',
            'audit_event_id'
        ]


class VerificationQueueItemSerializer(serializers.ModelSerializer):
    application_number = serializers.CharField(source='application.application_number', read_only=True)
    applicant_id = serializers.CharField(source='application.applicant.id', read_only=True)
    applicant_name = serializers.SerializerMethodField()
    scheme_code = serializers.CharField(source='application.scheme_version.scheme.code', read_only=True)
    scheme_name = serializers.CharField(source='application.scheme_version.scheme.name', read_only=True)
    document_type = serializers.SerializerMethodField()
    assigned_to_name = serializers.CharField(source='assigned_to.username', read_only=True)
    reviewed_by_name = serializers.CharField(source='reviewed_by.username', read_only=True)

    class Meta:
        model = VerificationQueueItem
        fields = [
            'id', 'application', 'application_number', 'applicant_id', 'applicant_name',
            'scheme_code', 'scheme_name', 'document', 'document_type',
            'item_type', 'target_identifier', 'conflict_type', 'priority',
            'confidence_score', 'status', 'current_evidence_json',
            'ai_assistance_json', 'officer_remarks',
            'assigned_to', 'assigned_to_name', 'assigned_at',
            'reviewed_by', 'reviewed_by_name', 'reviewed_at',
            'created_at', 'updated_at'
        ]

    def get_applicant_name(self, obj):
        if obj.application and obj.application.applicant and obj.application.applicant.user:
            return obj.application.applicant.user.get_full_name() or obj.application.applicant.user.username
        return "Unknown Applicant"

    def get_document_type(self, obj):
        if obj.document:
            return obj.document.document_type
        return obj.ai_assistance_json.get('document_type', '')


class VerifyFieldRequestSerializer(serializers.Serializer):
    field_code = serializers.CharField(required=True)
    verified_value = serializers.JSONField(required=True)
    reason = serializers.CharField(required=False, default="")
    block_id = serializers.UUIDField(required=False, allow_null=True, default=None)


class VerifyDocumentRequestSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, default="Officer verified documentary evidence.")


class ResolveConflictRequestSerializer(serializers.Serializer):
    decision_action = serializers.CharField(required=True)
    chosen_value = serializers.JSONField(required=True)
    reason = serializers.CharField(required=True)


class ReopenVerificationRequestSerializer(serializers.Serializer):
    reason = serializers.CharField(required=True)


class AssignQueueItemRequestSerializer(serializers.Serializer):
    officer_id = serializers.UUIDField(required=False, allow_null=True, default=None)


class QueueActionReasonSerializer(serializers.Serializer):
    reason = serializers.CharField(required=True)
