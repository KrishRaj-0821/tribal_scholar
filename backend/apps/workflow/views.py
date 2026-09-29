from rest_framework import viewsets, filters, mixins
from apps.accounts.permissions import IsSchemeAdmin, IsOfficerOrAdmin
from apps.audit.services import log_audit_event
from .models import WorkflowDefinition, WorkflowState, WorkflowTransition, ApplicationStatusHistory
from .serializers import (
    WorkflowDefinitionSerializer, WorkflowStateSerializer,
    WorkflowTransitionSerializer, ApplicationStatusHistorySerializer
)

class WorkflowDefinitionViewSet(viewsets.ModelViewSet):
    """
    Endpoints for configuring workflow state machines.
    Mutations restricted to Scheme Administrators.
    """
    queryset = WorkflowDefinition.objects.select_related('scheme_version').prefetch_related('states', 'transitions').all()
    serializer_class = WorkflowDefinitionSerializer
    permission_classes = [IsSchemeAdmin]
    filter_backends = [filters.SearchFilter]
    search_fields = ['name', 'scheme_version__scheme__code', 'scheme_version__academic_year']

    def perform_create(self, serializer):
        instance = serializer.save()
        log_audit_event(
            entity_type="WorkflowDefinition",
            entity_id=str(instance.id),
            action="CREATE",
            actor=self.request.user if self.request.user.is_authenticated else None,
            after_json=serializer.data,
            reason="Configured workflow definition for scheme version."
        )


class WorkflowStateViewSet(viewsets.ModelViewSet):
    queryset = WorkflowState.objects.select_related('workflow').all()
    serializer_class = WorkflowStateSerializer
    permission_classes = [IsSchemeAdmin]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['sequence']


class WorkflowTransitionViewSet(viewsets.ModelViewSet):
    queryset = WorkflowTransition.objects.select_related('workflow', 'from_state', 'to_state').all()
    serializer_class = WorkflowTransitionSerializer
    permission_classes = [IsSchemeAdmin]


class ApplicationStatusHistoryViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """
    Read-only view for immutable application status history.
    Available to Officers, Admins, and relevant applicants.
    """
    queryset = ApplicationStatusHistory.objects.select_related('application', 'from_state', 'to_state', 'changed_by').all()
    serializer_class = ApplicationStatusHistorySerializer
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['created_at']
