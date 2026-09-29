from rest_framework import serializers
from .models import (
    Scheme, SchemeVersion, SchemeRule, ReferenceSet, ReferenceSetItem,
    SchemeQuota, SelectionMethod, InstitutionEligibility,
    RuleStatus, RuleOperator, RuleCategory
)
from apps.documents.serializers import SourceDocumentSerializer

class ReferenceSetItemSerializer(serializers.ModelSerializer):
    source_document_title = serializers.CharField(source='source_document.title', read_only=True)

    class Meta:
        model = ReferenceSetItem
        fields = [
            'id', 'reference_set', 'external_code', 'name',
            'metadata_json', 'valid_from', 'valid_to',
            'source_document', 'source_document_title',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate(self, attrs):
        if not attrs.get('source_document') and (not self.instance or not self.instance.source_document):
            raise serializers.ValidationError({"source_document": "A ReferenceSetItem must maintain source document provenance."})
        return attrs


class ReferenceSetSerializer(serializers.ModelSerializer):
    items = ReferenceSetItemSerializer(many=True, read_only=True)
    item_count = serializers.IntegerField(source='items.count', read_only=True)
    dataset_status_display = serializers.CharField(source='get_dataset_status_display', read_only=True)

    class Meta:
        model = ReferenceSet
        fields = [
            'id', 'code', 'name', 'description', 'dataset_status', 'dataset_status_display',
            'record_count_expected', 'record_count_loaded', 'coverage_percentage',
            'source_document', 'verified_at',
            'item_count', 'items', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'coverage_percentage', 'created_at', 'updated_at']


class SchemeRuleSerializer(serializers.ModelSerializer):
    category_display = serializers.CharField(source='get_category_display', read_only=True)
    operator_display = serializers.CharField(source='get_operator_display', read_only=True)
    severity_display = serializers.CharField(source='get_severity_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    source_document_title = serializers.CharField(source='source_document.title', read_only=True)
    reference_set_code = serializers.CharField(source='reference_set.code', read_only=True)

    class Meta:
        model = SchemeRule
        fields = [
            'id', 'scheme_version', 'rule_code', 'category', 'category_display',
            'field_path', 'operator', 'operator_display', 'value',
            'reference_set', 'reference_set_code',
            'failure_message', 'severity', 'severity_display',
            'requires_human_review', 'preference_type',
            'source_document', 'source_document_title', 'source_excerpt', 'confidence',
            'status', 'status_display'
        ]
        read_only_fields = ['id']

    def validate(self, attrs):
        source_doc = attrs.get('source_document') or (self.instance.source_document if self.instance else None)
        if not source_doc:
            raise serializers.ValidationError({"source_document": "A SchemeRule must always reference a valid SourceDocument."})

        operator = attrs.get('operator') or (self.instance.operator if self.instance else None)
        if operator == RuleOperator.IN_SET and not (attrs.get('reference_set') or (self.instance and self.instance.reference_set)):
            raise serializers.ValidationError({"reference_set": "Rules using IN_SET operator must specify a ReferenceSet."})

        return attrs


class SchemeQuotaSerializer(serializers.ModelSerializer):
    gender_display = serializers.CharField(source='get_gender_display', read_only=True)
    source_document_title = serializers.CharField(source='source_document.title', read_only=True)

    class Meta:
        model = SchemeQuota
        fields = [
            'id', 'scheme_version', 'quota_code', 'total_capacity',
            'category', 'gender', 'gender_display', 'preference_group',
            'reserved_capacity', 'effective_from', 'effective_to',
            'source_document', 'source_document_title', 'status',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class SelectionMethodSerializer(serializers.ModelSerializer):
    source_document_title = serializers.CharField(source='source_document.title', read_only=True)

    class Meta:
        model = SelectionMethod
        fields = [
            'id', 'scheme_version', 'code', 'name',
            'human_decision_required', 'description',
            'source_document', 'source_document_title',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class InstitutionEligibilitySerializer(serializers.ModelSerializer):
    institution_name = serializers.CharField(source='institution.name', read_only=True)
    institution_code = serializers.CharField(source='institution.external_code', read_only=True)
    eligibility_status_display = serializers.CharField(source='get_eligibility_status_display', read_only=True)
    source_document_title = serializers.CharField(source='source_document.title', read_only=True)

    class Meta:
        model = InstitutionEligibility
        fields = [
            'id', 'scheme_version', 'institution', 'institution_name', 'institution_code',
            'course_name', 'course_code', 'eligibility_status', 'eligibility_status_display',
            'source_document', 'source_document_title', 'valid_from', 'valid_to',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class SchemeVersionSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    source_document_title = serializers.CharField(source='source_document.title', read_only=True)
    rules = SchemeRuleSerializer(many=True, read_only=True)
    quotas = SchemeQuotaSerializer(many=True, read_only=True)
    selection_methods = SelectionMethodSerializer(many=True, read_only=True)
    rule_count = serializers.IntegerField(source='rules.count', read_only=True)
    has_workflow = serializers.SerializerMethodField()

    class Meta:
        model = SchemeVersion
        fields = [
            'id', 'scheme', 'academic_year', 'version_number',
            'status', 'status_display', 'effective_from', 'effective_to',
            'source_document', 'source_document_title',
            'rule_count', 'rules', 'quotas', 'selection_methods', 'has_workflow',
            'created_at', 'approved_at'
        ]
        read_only_fields = ['id', 'created_at']

    def get_has_workflow(self, obj) -> bool:
        return hasattr(obj, 'workflow') and obj.workflow.active

    def validate(self, attrs):
        if not attrs.get('academic_year') and (not self.instance or not self.instance.academic_year):
            raise serializers.ValidationError({"academic_year": "Academic year is mandatory for SchemeVersion."})
        if not attrs.get('source_document') and (not self.instance or not self.instance.source_document):
            raise serializers.ValidationError({"source_document": "Source document provenance is mandatory for SchemeVersion."})
        return attrs


class SchemeSerializer(serializers.ModelSerializer):
    scheme_type_display = serializers.CharField(source='get_scheme_type_display', read_only=True)
    versions = SchemeVersionSerializer(many=True, read_only=True)
    version_count = serializers.IntegerField(source='versions.count', read_only=True)

    class Meta:
        model = Scheme
        fields = [
            'id', 'code', 'name', 'description', 'ministry',
            'scheme_type', 'scheme_type_display', 'active',
            'version_count', 'versions',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
