from rest_framework import serializers
from .models import SMSNotification, Notification


class SMSNotificationSerializer(serializers.ModelSerializer):
    """
    Safe public serializer for applicant inspection of SMS delivery receipts.
    Guarantees no internal provider secrets or PII are exposed.
    """
    class Meta:
        model = SMSNotification
        fields = [
            'id',
            'notification_type',
            'recipient_phone_masked',
            'status',
            'provider',
            'provider_request_id',
            'message_length',
            'failure_reason',
            'created_at',
            'sent_at'
        ]
        read_only_fields = fields


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = '__all__'
