from django.contrib import admin
from .models import Notification

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['title', 'recipient', 'channel', 'status', 'created_at']
    list_filter = ['channel', 'status', 'created_at']
    search_fields = ['title', 'recipient__username', 'message']
