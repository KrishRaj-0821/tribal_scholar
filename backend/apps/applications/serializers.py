from rest_framework import serializers
from .models import (
    Application, EligibilityEvaluation, ApplicationFieldDefinition,
    ApplicationFieldValue, ApplicationDeficiency, EligibilityInputSnapshot,
    FieldConflict, ApplicationSubmissionSnapshot
)


class ApplicationSerializer(serializers.ModelSerializer):
    scheme_code = serializers.CharField(source='scheme_version.scheme.code', read_only=True)
    academic_year = serializers.CharField(source='scheme_version.academic_year', read_only=True)
    current_state_code = serializers.CharField(source='current_state.code', read_only=True)
    last_modified_by_username = serializers.CharField(source='last_modified_by.username', read_only=True, allow_null=True)

    class Meta:
        model = Application
        fields = [
            'id', 'application_number', 'applicant', 'scheme_version',
            'scheme_code', 'academic_year', 'current_state', 'current_state_code',
            'revision_number', 'last_modified_at', 'last_modified_by', 'last_modified_by_username',
            'submission_data_json', 'is_synthetic', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'revision_number', 'last_modified_at', 'last_modified_by', 'created_at', 'updated_at']


class EligibilityEvaluationSerializer(serializers.ModelSerializer):
    class Meta:
        model = EligibilityEvaluation
        fields = [
            'id', 'application', 'scheme_version', 'evaluated_at',
            'engine_version', 'result', 'result_hash'
        ]
        read_only_fields = ['id', 'evaluated_at', 'result_hash']


class ApplicationFieldDefinitionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ApplicationFieldDefinition
        fields = [
            'id', 'scheme_version', 'field_code', 'label', 'description',
            'data_type', 'required', 'applicant_visible', 'officer_visible',
            'editable_until_state', 'validation_schema', 'display_order',
            'section', 'source_document', 'source_excerpt', 'status'
        ]


class ApplicationFieldValueSerializer(serializers.ModelSerializer):
    field_code = serializers.CharField(source='field_definition.field_code', read_only=True)

    class Meta:
        model = ApplicationFieldValue
        fields = [
            'id', 'application', 'field_definition', 'field_code',
            'value_json', 'source', 'verification_status', 'confidence', 'entered_by',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class ApplicationDeficiencySerializer(serializers.ModelSerializer):
    raised_by_username = serializers.CharField(source='raised_by.username', read_only=True)
    resolved_by_username = serializers.CharField(source='resolved_by.username', read_only=True, allow_null=True)

    class Meta:
        model = ApplicationDeficiency
        fields = [
            'id', 'application', 'deficiency_code', 'field_code',
            'document_type', 'description', 'severity', 'raised_by',
            'raised_by_username', 'raised_at', 'due_at', 'status',
            'resolution_text', 'resolved_by', 'resolved_by_username',
            'resolved_at'
        ]
        read_only_fields = ['id', 'raised_by', 'raised_at', 'resolved_by', 'resolved_at']


class EligibilityInputSnapshotSerializer(serializers.ModelSerializer):
    class Meta:
        model = EligibilityInputSnapshot
        fields = ['id', 'evaluation', 'payload_json', 'payload_hash', 'created_at']
        read_only_fields = ['id', 'created_at', 'payload_hash']


class FieldConflictSerializer(serializers.ModelSerializer):
    resolved_by_username = serializers.CharField(source='resolved_by.username', read_only=True, allow_null=True)

    class Meta:
        model = FieldConflict
        fields = [
            'id', 'application', 'field_code', 'values_json',
            'source_values', 'severity', 'status', 'created_at',
            'resolved_by', 'resolved_by_username', 'resolution', 'resolved_at'
        ]
        read_only_fields = ['id', 'created_at', 'resolved_by', 'resolved_at']


class ApplicationSubmissionSnapshotSerializer(serializers.ModelSerializer):
    class Meta:
        model = ApplicationSubmissionSnapshot
        fields = [
            'id', 'application', 'revision_number', 'submitted_at',
            'applicant_data_json', 'form_values_json', 'document_manifest_json',
            'scheme_version', 'snapshot_hash'
        ]
        read_only_fields = ['id', 'revision_number', 'submitted_at', 'snapshot_hash']

