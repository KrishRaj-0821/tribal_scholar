from rest_framework import serializers
from .models import SourceDocument, ApplicantDocument

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
            'id', 'applicant', 'document_type', 'file_name',
            'checksum', 'ocr_confidence_score', 'is_verified_by_officer',
            'created_at'
        ]
        read_only_fields = ['id', 'ocr_confidence_score', 'is_verified_by_officer', 'created_at']
