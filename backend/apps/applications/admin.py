from django.contrib import admin
from .models import Application, EligibilityEvaluation

@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = ['application_number', 'applicant', 'scheme_version', 'current_state', 'is_synthetic', 'created_at']
    list_filter = ['scheme_version__scheme', 'current_state', 'is_synthetic']
    search_fields = ['application_number', 'applicant__user__username']


@admin.register(EligibilityEvaluation)
class EligibilityEvaluationAdmin(admin.ModelAdmin):
    list_display = ['application', 'scheme_version', 'evaluated_at', 'engine_version', 'result_hash']
    list_filter = ['scheme_version__scheme', 'engine_version']
    search_fields = ['application__application_number', 'result_hash']
    readonly_fields = ['id', 'application', 'scheme_version', 'evaluated_at', 'engine_version', 'result', 'result_hash']
