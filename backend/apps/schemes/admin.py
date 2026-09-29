from django.contrib import admin
from .models import (
    Scheme, SchemeVersion, SchemeRule, ReferenceSet, ReferenceSetItem,
    SchemeQuota, SelectionMethod, InstitutionEligibility
)

class SchemeRuleInline(admin.TabularInline):
    model = SchemeRule
    extra = 0
    fields = ['rule_code', 'category', 'field_path', 'operator', 'value', 'reference_set', 'severity', 'status']

class SchemeQuotaInline(admin.TabularInline):
    model = SchemeQuota
    extra = 0
    fields = ['quota_code', 'total_capacity', 'category', 'gender', 'reserved_capacity', 'source_document']

class SelectionMethodInline(admin.TabularInline):
    model = SelectionMethod
    extra = 0
    fields = ['code', 'name', 'human_decision_required', 'source_document']

@admin.register(Scheme)
class SchemeAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'scheme_type', 'ministry', 'active', 'created_at']
    list_filter = ['scheme_type', 'active']
    search_fields = ['code', 'name', 'description']

@admin.register(SchemeVersion)
class SchemeVersionAdmin(admin.ModelAdmin):
    list_display = ['scheme', 'academic_year', 'version_number', 'status', 'effective_from', 'effective_to']
    list_filter = ['status', 'academic_year', 'scheme']
    search_fields = ['scheme__code', 'scheme__name', 'academic_year']
    inlines = [SchemeRuleInline, SchemeQuotaInline, SelectionMethodInline]

@admin.register(SchemeRule)
class SchemeRuleAdmin(admin.ModelAdmin):
    list_display = ['rule_code', 'scheme_version', 'category', 'operator', 'severity', 'status', 'requires_human_review']
    list_filter = ['category', 'operator', 'severity', 'status', 'requires_human_review', 'scheme_version__scheme']
    search_fields = ['rule_code', 'field_path', 'failure_message', 'source_excerpt']

class ReferenceSetItemInline(admin.TabularInline):
    model = ReferenceSetItem
    extra = 0
    fields = ['external_code', 'name', 'source_document']

@admin.register(ReferenceSet)
class ReferenceSetAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'dataset_status', 'record_count_loaded', 'record_count_expected', 'coverage_percentage', 'created_at']
    list_filter = ['dataset_status']
    search_fields = ['code', 'name']
    inlines = [ReferenceSetItemInline]

@admin.register(ReferenceSetItem)
class ReferenceSetItemAdmin(admin.ModelAdmin):
    list_display = ['name', 'external_code', 'reference_set', 'source_document']
    list_filter = ['reference_set']
    search_fields = ['name', 'external_code']

@admin.register(SchemeQuota)
class SchemeQuotaAdmin(admin.ModelAdmin):
    list_display = ['quota_code', 'scheme_version', 'total_capacity', 'category', 'gender', 'reserved_capacity']
    list_filter = ['category', 'gender', 'status', 'scheme_version__scheme']
    search_fields = ['quota_code']

@admin.register(SelectionMethod)
class SelectionMethodAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'scheme_version', 'human_decision_required']
    list_filter = ['human_decision_required', 'scheme_version__scheme']
    search_fields = ['code', 'name']

@admin.register(InstitutionEligibility)
class InstitutionEligibilityAdmin(admin.ModelAdmin):
    list_display = ['institution', 'course_name', 'eligibility_status', 'scheme_version']
    list_filter = ['eligibility_status', 'scheme_version__scheme']
    search_fields = ['course_name', 'institution__name']
