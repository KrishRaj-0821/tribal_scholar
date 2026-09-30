from rest_framework import serializers
from .models import SourceDocument, ApplicantDocument, DocumentVersion


class SourceDocumentSerializer(serializers.ModelSerializer):
    source_type_display = serializers.CharField(source='get_source_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = SourceDocument
        fields = [
            'id', 'title', 'source_type', 'source_type_display', 'source_url',
            'scheme', 'academic_year', 'document_date', 'retrieved_at',
            'checksum', 'content_hash', 'status', 'status_display',
            'supersedes_source', 'notes'
        ]
        read_only_fields = ['id', 'retrieved_at']

    def validate_checksum(self, value):
        if len(value) != 64:
            raise serializers.ValidationError("Checksum must be a valid 64-character SHA-256 string.")
        return value


class ApplicantDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = ApplicantDocument
        fields = [
            'id', 'applicant', 'document_type', 'file_name', 'original_filename',
            'checksum', 'sha256', 'lifecycle_status', 'malware_scan_status',
            'content_validation_status', 'ocr_confidence_score', 'is_verified_by_officer',
            'created_at'
        ]
        read_only_fields = [
            'id', 'ocr_confidence_score', 'is_verified_by_officer', 'created_at',
            'sha256', 'checksum', 'lifecycle_status', 'malware_scan_status',
            'content_validation_status'
        ]


class DocumentUploadResponseSerializer(serializers.Serializer):
    document_id = serializers.UUIDField(source='id')
    status = serializers.CharField(source='lifecycle_status')
    sha256 = serializers.CharField()
    detected_mime_type = serializers.CharField()
    size_bytes = serializers.IntegerField(source='file_size_bytes')
    lifecycle_status = serializers.CharField()


class DocumentStatusSerializer(serializers.Serializer):
    document_type = serializers.CharField()
    version = serializers.SerializerMethodField()
    size = serializers.IntegerField(source='file_size_bytes')
    mime = serializers.CharField(source='detected_mime_type')
    sha256 = serializers.CharField()
    scan_status = serializers.CharField(source='malware_scan_status')
    validation_status = serializers.CharField(source='content_validation_status')
    lifecycle_status = serializers.CharField()
    uploaded_at = serializers.DateTimeField()
    verification_status = serializers.CharField(source='lifecycle_status')

    def get_version(self, obj):
        latest = obj.versions.order_by('-version_number').first()
        return latest.version_number if latest else 1


class OCRJobStatusSerializer(serializers.ModelSerializer):
    from .models import OCRJob
    class Meta:
        from .models import OCRJob
        model = OCRJob
        fields = [
            'id', 'document_id', 'status', 'attempts', 'created_at',
            'started_at', 'completed_at', 'failure_code', 'failure_message',
            'engine_name', 'pipeline_version'
        ]
        read_only_fields = fields


class OCRBlockSerializer(serializers.ModelSerializer):
    bounding_box = serializers.SerializerMethodField()

    class Meta:
        from .models import OCRBlock
        model = OCRBlock
        fields = [
            'id', 'extracted_text', 'confidence', 'bounding_box',
            'polygon', 'block_type', 'language', 'reading_order'
        ]

    def get_bounding_box(self, obj):
        return {
            'x': obj.bbox_x,
            'y': obj.bbox_y,
            'width': obj.bbox_width,
            'height': obj.bbox_height
        }


class OCRPageSerializer(serializers.ModelSerializer):
    blocks = OCRBlockSerializer(many=True, read_only=True)

    class Meta:
        from .models import OCRPage
        model = OCRPage
        fields = [
            'id', 'page_number', 'width', 'height', 'rotation',
            'processing_status', 'page_confidence', 'blocks'
        ]


class OCRResultMetadataSerializer(serializers.ModelSerializer):
    pages = OCRPageSerializer(many=True, read_only=True)

    class Meta:
        from .models import OCRResult
        model = OCRResult
        fields = [
            'id', 'document_id', 'page_count', 'engine_name',
            'engine_version', 'pipeline_version', 'language_metadata',
            'result_hash', 'created_at', 'pages'
        ]


class DocumentClassificationSerializer(serializers.ModelSerializer):
    class Meta:
        from .models import DocumentClassificationResult
        model = DocumentClassificationResult
        fields = [
            'id', 'document_id', 'predicted_type', 'confidence',
            'classifier_version', 'classification_method',
            'evidence_summary', 'created_at'
        ]


class ProvisionalExtractedFieldSerializer(serializers.ModelSerializer):
    class Meta:
        from .models import ProvisionalExtractedField
        model = ProvisionalExtractedField
        fields = [
            'id', 'document_id', 'field_code', 'field_label',
            'raw_value', 'normalized_value', 'confidence',
            'trust_level', 'extraction_method', 'pipeline_version',
            'page_number', 'bounding_box', 'created_at'
        ]
