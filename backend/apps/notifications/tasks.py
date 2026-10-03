import logging
from celery import shared_task
from django.utils import timezone
from .models import SMSNotification, SMSDeliveryStatus
from .providers.fast2sms import Fast2SMSProvider, get_sms_provider

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=10,
    retry_backoff=True,
    retry_backoff_max=120,
    acks_late=True
)
def dispatch_sms_notification_task(self, notification_id: str, phone_number: str, message: str):
    """
    Asynchronous Celery task for delivering an SMS via Fast2SMS.
    Updates the persistent SMSNotification delivery record and handles bounded retries.
    """
    try:
        notification = SMSNotification.objects.get(id=notification_id)
    except SMSNotification.DoesNotExist:
        logger.error("SMSNotification %s not found. Aborting dispatch.", notification_id)
        return

    # Check if already in terminal state
    if notification.status in (SMSDeliveryStatus.SENT, SMSDeliveryStatus.DEV_SKIPPED):
        logger.info("SMSNotification %s already finalized (%s).", notification_id, notification.status)
        return

    notification.status = SMSDeliveryStatus.SENDING
    notification.save(update_fields=['status'])

    provider = get_sms_provider()
    result = provider.send_sms(phone_number=phone_number, message=message)


    if result.success:
        notification.status = SMSDeliveryStatus.SENT if result.status == 'SENT' else SMSDeliveryStatus.DEV_SKIPPED
        notification.provider_request_id = result.provider_request_id
        notification.sent_at = timezone.now()
        notification.failure_reason = ''
        notification.save(update_fields=['status', 'provider_request_id', 'sent_at', 'failure_reason'])
        logger.info("SMSNotification %s delivered successfully via Fast2SMS.", notification_id)
    elif result.status == 'RETRY_PENDING':
        # Transient failure (network/5xx) -> trigger Celery retry
        notification.status = SMSDeliveryStatus.RETRY_PENDING
        notification.failure_reason = result.failure_reason or 'Transient network/gateway error'
        notification.retry_count = self.request.retries + 1
        notification.save(update_fields=['status', 'failure_reason', 'retry_count'])

        logger.warning(
            "SMSNotification %s failed with transient error: %s. Scheduling retry %d/3...",
            notification_id,
            result.failure_reason,
            notification.retry_count
        )
        try:
            raise self.retry(exc=Exception(result.failure_reason))
        except self.MaxRetriesExceededError:
            notification.status = SMSDeliveryStatus.FAILED
            notification.failure_reason = f"Max retries exceeded: {result.failure_reason}"
            notification.save(update_fields=['status', 'failure_reason'])
            logger.error("SMSNotification %s permanently failed after max retries.", notification_id)
    else:
        # Permanent failure (invalid number, client 4xx, etc.) -> DO NOT retry
        notification.status = SMSDeliveryStatus.FAILED
        notification.failure_reason = result.failure_reason or 'Provider rejected message'
        notification.save(update_fields=['status', 'failure_reason'])
        logger.warning(
            "SMSNotification %s permanently rejected: %s",
            notification_id,
            notification.failure_reason
        )
