from django.contrib import admin
from .models import ApplicantProfile

@admin.register(ApplicantProfile)
class ApplicantProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'community', 'annual_family_income', 'is_disabled', 'is_synthetic', 'created_at']
    list_filter = ['community', 'is_disabled', 'is_synthetic']
    search_fields = ['user__username', 'caste_certificate_number', 'income_certificate_number']
