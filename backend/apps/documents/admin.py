from django.contrib import admin
from .models import SourceDocument, ApplicantDocument

@admin.register(SourceDocument)
class SourceDocumentAdmin(admin.ModelAdmin):
    list_display = ['title', 'source_type', 'scheme', 'academic_year', 'document_date', 'status']
    list_filter = ['source_type', 'academic_year', 'status', 'scheme']
    search_fields = ['title', 'notes', 'checksum']
    readonly_fields = ['retrieved_at']

@admin.register(ApplicantDocument)
class ApplicantDocumentAdmin(admin.ModelAdmin):
    list_display = ['file_name', 'applicant', 'document_type', 'ocr_confidence_score', 'is_verified_by_officer', 'created_at']
    list_filter = ['document_type', 'is_verified_by_officer', 'created_at']
    search_fields = ['file_name', 'applicant__username', 'checksum']
