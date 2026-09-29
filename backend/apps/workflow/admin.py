from django.contrib import admin
from .models import WorkflowDefinition, WorkflowState, WorkflowTransition, ApplicationStatusHistory

class WorkflowStateInline(admin.TabularInline):
    model = WorkflowState
    extra = 0
    fields = ['code', 'display_name', 'sequence', 'applicant_visible', 'officer_visible', 'terminal']

class WorkflowTransitionInline(admin.TabularInline):
    model = WorkflowTransition
    extra = 0
    fields = ['from_state', 'to_state', 'required_role', 'requires_reason']

@admin.register(WorkflowDefinition)
class WorkflowDefinitionAdmin(admin.ModelAdmin):
    list_display = ['name', 'scheme_version', 'active', 'created_at']
    list_filter = ['active']
    inlines = [WorkflowStateInline, WorkflowTransitionInline]

@admin.register(ApplicationStatusHistory)
class ApplicationStatusHistoryAdmin(admin.ModelAdmin):
    list_display = ['application', 'from_state', 'to_state', 'changed_by', 'created_at']
    readonly_fields = ['application', 'from_state', 'to_state', 'changed_by', 'reason', 'created_at']

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
