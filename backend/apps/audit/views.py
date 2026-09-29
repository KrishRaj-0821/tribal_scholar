from rest_framework import viewsets, filters
from apps.accounts.permissions import IsOfficerOrAdmin
from .models import AuditLog
from .serializers import AuditLogSerializer

class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only endpoint for statutory, append-only audit records.
    Restricted to verified Officers and System Administrators.
    """
    queryset = AuditLog.objects.select_related('actor').all()
    serializer_class = AuditLogSerializer
    permission_classes = [IsOfficerOrAdmin]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['entity_type', 'entity_id', 'action', 'actor_role', 'reason']
    ordering_fields = ['created_at']
