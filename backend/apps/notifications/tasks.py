import logging
from celery import shared_task
from django.utils import timezone
from .models import SMSNotification, SMSDeliveryStatus, SMSNotificationType
from .providers.fast2sms import Fast2SMSProvider, get_sms_provider, mask_phone_number

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=10,
    retry_backoff=True,
    retry_backoff_max=120,
    acks_late=True
)
def dispatch_sms_notification_task(
    self,
    notification_id: str,
    phone_number: str,
    message: str,
    otp_code: str = '',
    expiry_minutes: int = 5,
    **kwargs
):
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
    if notification.status in (SMSDeliveryStatus.SENT_TO_PROVIDER, SMSDeliveryStatus.DELIVERED, SMSDeliveryStatus.DEV_SKIPPED):
        logger.info("SMSNotification %s already finalized (%s).", notification_id, notification.status)
        return

    notification.status = SMSDeliveryStatus.SENDING
    notification.save(update_fields=['status'])

    provider = get_sms_provider()

    # Route OTP via send_otp if this is an OTP notification and code is provided
    if notification.notification_type == SMSNotificationType.OTP and otp_code:
        result = provider.send_otp(
            phone_number=phone_number,
            otp_code=otp_code,
            expiry_minutes=expiry_minutes,
            message=message,
            **kwargs
        )
    else:
        result = provider.send_sms(
            phone_number=phone_number,
            message=message,
            **kwargs
        )

    if result.success:
        notification.status = SMSDeliveryStatus.SENT_TO_PROVIDER if result.status == 'SENT_TO_PROVIDER' else SMSDeliveryStatus.DEV_SKIPPED
        notification.provider_request_id = result.provider_request_id
        notification.sent_at = timezone.now()
        notification.failure_reason = ''
        notification.save(update_fields=['status', 'provider_request_id', 'sent_at', 'failure_reason'])
        logger.info("SMSNotification %s dispatched to Fast2SMS provider successfully.", notification_id)

    elif result.status == 'RETRY_PENDING':
        # Transient failure (network/5xx) -> trigger Celery retry
        notification.status = SMSDeliveryStatus.RETRY_PENDING
        notification.failure_reason = result.failure_reason or 'Transient network/gateway error'
        notification.retry_count = getattr(self.request, 'retries', 0) + 1
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
        # Permanent failure (invalid number, client 4xx, IP restriction, balance, KYC) -> DO NOT retry
        notification.status = SMSDeliveryStatus.FAILED
        notification.failure_reason = result.failure_reason or 'Provider rejected message'
        notification.save(update_fields=['status', 'failure_reason'])
        logger.warning(
            "SMSNotification %s permanently rejected: %s",
            notification_id,
            notification.failure_reason
        )


@shared_task(bind=True)
def check_worker_egress_ip_task(self):
    """
    Diagnostic Celery task executed directly on the Celery worker container.
    Queries both https://api.ipify.org and https://ifconfig.me to inspect
    the worker's active outbound egress IPv4 address.
    """
    import urllib.request
    import socket
    results = {
        "worker_hostname": socket.gethostname(),
        "task_name": "apps.notifications.tasks.check_worker_egress_ip_task",
        "worker_id": getattr(self.request, 'hostname', None) or socket.gethostname()
    }
    for url, key in [('https://api.ipify.org', 'api_ipify'), ('https://ifconfig.me', 'ifconfig_me')]:
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'curl/8.0.0'})
            with urllib.request.urlopen(req, timeout=7) as resp:
                results[key] = resp.read().decode('utf-8').strip()
        except Exception as e:
            results[key] = f"error: {str(e)}"
    results["ips_match"] = (
        results.get("api_ipify") == results.get("ifconfig_me") and
        "error" not in results.get("api_ipify", "")
    )
    return results


@shared_task(bind=True)
def probe_fast2sms_connectivity_task(self, test_phone: str = "9122671902"):
    """
    Diagnostic Celery task executed directly on the Celery worker container
    to verify Fast2SMS API communication and report provider responses safely.
    Masks PII, never logs API keys.
    """
    from .providers.fast2sms import get_sms_provider, mask_phone_number
    provider = get_sms_provider()
    masked = mask_phone_number(test_phone)
    result = provider.send_sms(
        phone_number=test_phone,
        message="MoTA Tribal Scholar Worker Connectivity Probe."
    )
    return {
        "success": result.success,
        "status": result.status,
        "masked_phone": masked,
        "provider_request_id": result.provider_request_id,
        "message": result.message,
        "failure_reason": result.failure_reason,
        "raw_response": result.raw_response,
    }

