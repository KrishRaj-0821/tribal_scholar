from rest_framework import serializers
from .models import AuditLog

class AuditLogSerializer(serializers.ModelSerializer):
    actor_username = serializers.CharField(source='actor.username', read_only=True)

    class Meta:
        model = AuditLog
        fields = [
            'id', 'actor', 'actor_username', 'actor_role',
            'entity_type', 'entity_id', 'action',
            'before_json', 'after_json', 'reason',
            'ip_address', 'created_at'
        ]
        read_only_fields = fields
