from django.contrib import admin
from .models import VerificationQueueItem

@admin.register(VerificationQueueItem)
class VerificationQueueItemAdmin(admin.ModelAdmin):
    list_display = ['application', 'item_type', 'target_identifier', 'confidence_score', 'status', 'reviewed_by', 'reviewed_at']
    list_filter = ['item_type', 'status']
    search_fields = ['application__application_number', 'target_identifier', 'officer_remarks']
