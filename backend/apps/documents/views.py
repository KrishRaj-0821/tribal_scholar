from rest_framework import viewsets, filters
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from apps.accounts.permissions import IsSchemeAdmin
from .models import SourceDocument
from .serializers import SourceDocumentSerializer

class SourceDocumentViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing authentic Source Documents and provenance registries.
    Mutations strictly restricted to authorized Scheme Administrators.
    """
    queryset = SourceDocument.objects.all()
    serializer_class = SourceDocumentSerializer
    permission_classes = [IsSchemeAdmin]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'academic_year', 'notes', 'source_type']
    ordering_fields = ['document_date', 'retrieved_at', 'academic_year']

    def perform_create(self, serializer):
        from apps.audit.services import log_audit_event
        instance = serializer.save()
        log_audit_event(
            entity_type="SourceDocument",
            entity_id=str(instance.id),
            action="CREATE",
            actor=self.request.user if self.request.user.is_authenticated else None,
            after_json=serializer.data,
            reason="Registered new official publication in source registry."
        )

    def perform_update(self, serializer):
        from apps.audit.services import log_audit_event
        before_data = SourceDocumentSerializer(serializer.instance).data
        instance = serializer.save()
        log_audit_event(
            entity_type="SourceDocument",
            entity_id=str(instance.id),
            action="UPDATE",
            actor=self.request.user if self.request.user.is_authenticated else None,
            before_json=before_data,
            after_json=serializer.data,
            reason="Updated source document metadata."
        )
