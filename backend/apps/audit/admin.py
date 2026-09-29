from django.contrib import admin
from .models import AuditLog

@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ['created_at', 'action', 'entity_type', 'entity_id', 'actor', 'actor_role', 'ip_address']
    list_filter = ['action', 'entity_type', 'actor_role']
    search_fields = ['entity_id', 'reason', 'actor__username', 'ip_address']
    readonly_fields = [
        'id', 'actor', 'actor_role', 'entity_type', 'entity_id',
        'action', 'before_json', 'after_json', 'reason', 'ip_address', 'created_at'
    ]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
