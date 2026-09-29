from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from apps.accounts.permissions import IsSchemeAdmin
from apps.audit.services import log_audit_event
from apps.core.services import validate_scheme_version_integrity
from .models import (
    Scheme, SchemeVersion, SchemeRule, ReferenceSet, ReferenceSetItem,
    SchemeQuota, SelectionMethod, InstitutionEligibility
)
from .serializers import (
    SchemeSerializer, SchemeVersionSerializer, SchemeRuleSerializer,
    ReferenceSetSerializer, ReferenceSetItemSerializer,
    SchemeQuotaSerializer, SelectionMethodSerializer, InstitutionEligibilitySerializer
)

class SchemeViewSet(viewsets.ModelViewSet):
    """
    Endpoints for MoTA Schemes. Mutations restricted to Scheme Administrators.
    """
    queryset = Scheme.objects.prefetch_related('versions').all()
    serializer_class = SchemeSerializer
    permission_classes = [IsSchemeAdmin]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['code', 'name', 'description']
    ordering_fields = ['code', 'name', 'created_at']

    def perform_create(self, serializer):
        instance = serializer.save()
        log_audit_event(
            entity_type="Scheme",
            entity_id=str(instance.id),
            action="CREATE",
            actor=self.request.user if self.request.user.is_authenticated else None,
            after_json=serializer.data,
            reason="Created new scheme definition."
        )

    def perform_update(self, serializer):
        before = SchemeSerializer(serializer.instance).data
        instance = serializer.save()
        log_audit_event(
            entity_type="Scheme",
            entity_id=str(instance.id),
            action="UPDATE",
            actor=self.request.user if self.request.user.is_authenticated else None,
            before_json=before,
            after_json=serializer.data,
            reason="Updated scheme master metadata."
        )


class SchemeVersionViewSet(viewsets.ModelViewSet):
    """
    Endpoints for academic-year Scheme Versions.
    """
    queryset = SchemeVersion.objects.select_related('scheme', 'source_document').prefetch_related('rules').all()
    serializer_class = SchemeVersionSerializer
    permission_classes = [IsSchemeAdmin]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['academic_year', 'scheme__code', 'scheme__name']
    ordering_fields = ['academic_year', 'version_number', 'created_at']

    @action(detail=True, methods=['get'])
    def validate_integrity(self, request, pk=None):
        """
        Explicitly triggers statutory validation rules on this SchemeVersion.
        """
        version = self.get_object()
        errors = validate_scheme_version_integrity(version)
        if errors:
            return Response(
                {
                    "valid": False,
                    "scheme": version.scheme.code,
                    "academic_year": version.academic_year,
                    "version_number": version.version_number,
                    "status": version.status,
                    "errors": errors
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        return Response({
            "valid": True,
            "scheme": version.scheme.code,
            "academic_year": version.academic_year,
            "version_number": version.version_number,
            "status": version.status,
            "message": "SchemeVersion complies with all statutory provenance and rule integrity checks."
        })

    def perform_create(self, serializer):
        instance = serializer.save()
        log_audit_event(
            entity_type="SchemeVersion",
            entity_id=str(instance.id),
            action="CREATE",
            actor=self.request.user if self.request.user.is_authenticated else None,
            after_json=serializer.data,
            reason="Created new academic-year scheme version."
        )


class SchemeRuleViewSet(viewsets.ModelViewSet):
    """
    Endpoints for declarative SchemeRules.
    """
    queryset = SchemeRule.objects.select_related('scheme_version', 'source_document', 'reference_set').all()
    serializer_class = SchemeRuleSerializer
    permission_classes = [IsSchemeAdmin]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['rule_code', 'field_path', 'failure_message', 'scheme_version__scheme__code']
    ordering_fields = ['rule_code', 'rule_type', 'severity']

    def perform_create(self, serializer):
        instance = serializer.save()
        log_audit_event(
            entity_type="SchemeRule",
            entity_id=str(instance.id),
            action="CREATE",
            actor=self.request.user if self.request.user.is_authenticated else None,
            after_json=serializer.data,
            reason=f"Added rule {instance.rule_code} to {instance.scheme_version}."
        )

    def perform_update(self, serializer):
        before = SchemeRuleSerializer(serializer.instance).data
        instance = serializer.save()
        log_audit_event(
            entity_type="SchemeRule",
            entity_id=str(instance.id),
            action="UPDATE",
            actor=self.request.user if self.request.user.is_authenticated else None,
            before_json=before,
            after_json=serializer.data,
            reason=f"Modified rule configuration for {instance.rule_code}."
        )

    def perform_destroy(self, instance):
        rule_code = instance.rule_code
        rule_id = str(instance.id)
        instance.delete()
        log_audit_event(
            entity_type="SchemeRule",
            entity_id=rule_id,
            action="DELETE",
            actor=self.request.user if self.request.user.is_authenticated else None,
            reason=f"Deleted rule {rule_code}."
        )


class ReferenceSetViewSet(viewsets.ModelViewSet):
    """
    Endpoints for Reference Sets (e.g. 265 Premier Institutes).
    """
    queryset = ReferenceSet.objects.prefetch_related('items').all()
    serializer_class = ReferenceSetSerializer
    permission_classes = [IsSchemeAdmin]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['code', 'name', 'description']


class ReferenceSetItemViewSet(viewsets.ModelViewSet):
    """
    Endpoints for individual items inside Reference Sets.
    """
    queryset = ReferenceSetItem.objects.select_related('reference_set', 'source_document').all()
    serializer_class = ReferenceSetItemSerializer
    permission_classes = [IsSchemeAdmin]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'external_code', 'reference_set__code']


class SchemeQuotaViewSet(viewsets.ModelViewSet):
    queryset = SchemeQuota.objects.select_related('scheme_version', 'source_document').all()
    serializer_class = SchemeQuotaSerializer
    permission_classes = [IsSchemeAdmin]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['quota_code', 'category']


class SelectionMethodViewSet(viewsets.ModelViewSet):
    queryset = SelectionMethod.objects.select_related('scheme_version', 'source_document').all()
    serializer_class = SelectionMethodSerializer
    permission_classes = [IsSchemeAdmin]
    filter_backends = [filters.SearchFilter]
    search_fields = ['code', 'name']


class InstitutionEligibilityViewSet(viewsets.ModelViewSet):
    queryset = InstitutionEligibility.objects.select_related('scheme_version', 'institution', 'source_document').all()
    serializer_class = InstitutionEligibilitySerializer
    permission_classes = [IsSchemeAdmin]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['course_name', 'institution__name']
