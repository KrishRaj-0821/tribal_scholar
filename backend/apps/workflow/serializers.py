from rest_framework import serializers
from .models import WorkflowDefinition, WorkflowState, WorkflowTransition, ApplicationStatusHistory

class WorkflowStateSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkflowState
        fields = [
            'id', 'workflow', 'code', 'display_name',
            'sequence', 'applicant_visible', 'officer_visible', 'terminal'
        ]
        read_only_fields = ['id']


class WorkflowTransitionSerializer(serializers.ModelSerializer):
    from_state_code = serializers.CharField(source='from_state.code', read_only=True)
    to_state_code = serializers.CharField(source='to_state.code', read_only=True)

    class Meta:
        model = WorkflowTransition
        fields = [
            'id', 'workflow', 'from_state', 'from_state_code',
            'to_state', 'to_state_code', 'required_role',
            'requires_reason', 'rule_condition_json'
        ]
        read_only_fields = ['id']


class WorkflowDefinitionSerializer(serializers.ModelSerializer):
    states = WorkflowStateSerializer(many=True, read_only=True)
    transitions = WorkflowTransitionSerializer(many=True, read_only=True)
    scheme_code = serializers.CharField(source='scheme_version.scheme.code', read_only=True)
    academic_year = serializers.CharField(source='scheme_version.academic_year', read_only=True)

    class Meta:
        model = WorkflowDefinition
        fields = [
            'id', 'scheme_version', 'scheme_code', 'academic_year',
            'name', 'active', 'states', 'transitions',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class ApplicationStatusHistorySerializer(serializers.ModelSerializer):
    from_state_name = serializers.CharField(source='from_state.display_name', read_only=True)
    to_state_name = serializers.CharField(source='to_state.display_name', read_only=True)
    changed_by_name = serializers.CharField(source='changed_by.username', read_only=True)

    class Meta:
        model = ApplicationStatusHistory
        fields = [
            'id', 'application', 'from_state', 'from_state_name',
            'to_state', 'to_state_name', 'changed_by', 'changed_by_name',
            'reason', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']
