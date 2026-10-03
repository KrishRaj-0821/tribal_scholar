import pytest
from unittest.mock import patch, MagicMock
from datetime import timedelta
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import check_password

from apps.notifications.providers.fast2sms import (
    normalize_phone_number,
    mask_phone_number,
    Fast2SMSProvider,
)
from apps.notifications.providers.base import SMSProviderResult
from apps.notifications.templates import (
    NotificationTemplate,
    render_template,
    TEMPLATES,
)

from apps.notifications.models import (
    SMSNotification,
    OTPVerification,
    NotificationStatus,
    NotificationType,
)
from apps.notifications.services import NotificationService, OTPService
from apps.notifications.tasks import dispatch_sms_notification_task

User = get_user_model()


# ==============================================================================
# 1. PHONE NORMALIZATION & MASKING TESTS
# ==============================================================================

class TestPhoneNormalization:
    def test_standard_10_digit_indian_number(self):
        assert normalize_phone_number("9876543210") == "9876543210"
        assert normalize_phone_number("8123456789") == "8123456789"
        assert normalize_phone_number("7012345678") == "7012345678"
        assert normalize_phone_number("6301234567") == "6301234567"

    def test_leading_zero_stripped(self):
        assert normalize_phone_number("09876543210") == "9876543210"

    def test_plus_91_country_code_stripped(self):
        assert normalize_phone_number("+919876543210") == "9876543210"
        assert normalize_phone_number("+91 98765 43210") == "9876543210"

    def test_91_prefix_with_12_digits_stripped(self):
        assert normalize_phone_number("919876543210") == "9876543210"

    def test_formatted_with_dashes_spaces_parentheses(self):
        assert normalize_phone_number("+91 (987) 654-3210") == "9876543210"
        assert normalize_phone_number("987-654-3210") == "9876543210"

    def test_invalid_start_digits_rejected(self):
        # Indian mobile numbers must start with 6, 7, 8, or 9
        for invalid in ["1234567890", "2345678901", "3456789012", "4567890123", "5678901234"]:
            with pytest.raises(ValueError, match="must begin with 6, 7, 8, or 9"):
                normalize_phone_number(invalid)

    def test_invalid_lengths_rejected(self):
        with pytest.raises(ValueError, match="Invalid phone number length"):
            normalize_phone_number("98765")
        with pytest.raises(ValueError, match="Invalid phone number length"):
            normalize_phone_number("987654321012345")

    def test_empty_or_none_rejected(self):
        with pytest.raises(ValueError):
            normalize_phone_number("")
        with pytest.raises(ValueError):
            normalize_phone_number(None)

    def test_masking_standard_number(self):
        masked = mask_phone_number("9876543210")
        assert masked == "******3210"
        assert not masked.startswith("987654")

    def test_masking_short_or_empty_number(self):
        assert mask_phone_number("") == "******"
        assert mask_phone_number("123") == "******"


# ==============================================================================
# 2. TEMPLATE RENDERING TESTS
# ==============================================================================

class TestNotificationTemplates:
    def test_application_submitted_template(self):
        msg = render_template(
            NotificationTemplate.APPLICATION_SUBMITTED,
            application_id="APP-2026-ST-001"
        )
        assert "APP-2026-ST-001" in msg
        assert "submitted successfully" in msg
        # Sensitive details must not be in status notifications
        assert "caste" not in msg.lower()
        assert "income" not in msg.lower()

    def test_verification_completed_template(self):
        msg = render_template(
            NotificationTemplate.VERIFICATION_COMPLETED,
            application_id="APP-2026-ST-001"
        )
        assert "APP-2026-ST-001" in msg
        assert "reviewed" in msg

    def test_needs_more_evidence_template(self):
        msg = render_template(
            NotificationTemplate.NEEDS_MORE_EVIDENCE,
            application_id="APP-2026-ST-001"
        )
        assert "APP-2026-ST-001" in msg
        assert "Action required" in msg

    def test_otp_template(self):
        msg = render_template(
            NotificationTemplate.OTP,
            otp="749123",
            expiry_minutes=5
        )
        assert "749123" in msg
        assert "5 minutes" in msg

    def test_missing_template_parameter_raises_key_error(self):
        with pytest.raises(KeyError):
            render_template(NotificationTemplate.APPLICATION_SUBMITTED)


# ==============================================================================
# 3. FAST2SMS PROVIDER TESTS (MOCKED HTTP)
# ==============================================================================

class TestFast2SMSProviderMocked:
    @patch("apps.notifications.providers.fast2sms.requests.post")
    def test_successful_sms_delivery(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "return": True,
            "request_id": "fast2sms_req_9988",
            "message": ["SMS sent successfully."]
        }
        mock_post.return_value = mock_response

        provider = Fast2SMSProvider(api_key="mock_secret_key", enabled=True)
        result = provider.send_sms(
            phone_number="9876543210",
            message="Test message from Tribal Scholar",
            notification_type="APPLICATION_SUBMITTED"
        )

        assert result.success is True
        assert result.status == 'SENT'
        assert result.provider_request_id == "fast2sms_req_9988"
        assert result.is_transient_failure is False

        # Verify correct request structure as per Fast2SMS Quick SMS specification
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        assert kwargs["headers"]["Authorization"] == "mock_secret_key"
        assert kwargs["json"]["route"] == "q"
        assert kwargs["json"]["numbers"] == "9876543210"
        assert kwargs["json"]["message"] == "Test message from Tribal Scholar"

    @patch("apps.notifications.providers.fast2sms.requests.post")
    def test_provider_rejection_permanent_failure(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.json.return_value = {
            "return": False,
            "message": ["Invalid numbers parameter provided."]
        }
        mock_post.return_value = mock_response

        provider = Fast2SMSProvider(api_key="mock_secret_key", enabled=True)
        result = provider.send_sms(
            phone_number="9876543210",
            message="Test message",
            notification_type="APPLICATION_SUBMITTED"
        )

        assert result.success is False
        assert result.status == 'FAILED'
        assert result.is_transient_failure is False
        assert "Invalid numbers" in (result.failure_reason or "")

    @patch("apps.notifications.providers.fast2sms.requests.post")
    def test_provider_server_error_transient_failure(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 503
        mock_response.text = "Service Unavailable"
        mock_post.return_value = mock_response

        provider = Fast2SMSProvider(api_key="mock_secret_key", enabled=True)
        result = provider.send_sms(
            phone_number="9876543210",
            message="Test message",
            notification_type="APPLICATION_SUBMITTED"
        )

        assert result.success is False
        assert result.status == 'RETRY_PENDING'
        assert result.is_transient_failure is True

    @patch("apps.notifications.providers.fast2sms.requests.post")
    def test_network_timeout_transient_failure(self, mock_post):
        import requests
        mock_post.side_effect = requests.exceptions.Timeout("Connection timed out.")

        provider = Fast2SMSProvider(api_key="mock_secret_key", enabled=True)
        result = provider.send_sms(
            phone_number="9876543210",
            message="Test message",
            notification_type="APPLICATION_SUBMITTED"
        )

        assert result.success is False
        assert result.status == 'RETRY_PENDING'
        assert result.is_transient_failure is True
        assert "timeout" in (result.failure_reason or "").lower()

    @patch("apps.notifications.providers.fast2sms.requests.post")
    def test_dev_mode_skips_external_http_request(self, mock_post):
        provider = Fast2SMSProvider(api_key="", enabled=False)
        result = provider.send_sms(
            phone_number="9876543210",
            message="Test message",
            notification_type="APPLICATION_SUBMITTED"
        )

        # Must not call real HTTP endpoint when disabled
        mock_post.assert_not_called()
        assert result.success is True
        assert result.status == 'DEV_SKIPPED'
        assert result.provider_request_id == "DEV_MODE_MOCK_DISPATCH"


# ==============================================================================
# 4. CELERY ASYNCHRONOUS TASK RETRY TESTS
# ==============================================================================

@pytest.mark.django_db
class TestCeleryTaskRetries:
    @patch("apps.notifications.tasks.get_sms_provider")
    def test_successful_task_execution(self, mock_get_provider):
        mock_provider = MagicMock()
        mock_provider.send_sms.return_value = SMSProviderResult(
            success=True,
            status='SENT',
            provider_request_id="fast2sms_req_task_1",
            raw_response={"return": True}
        )
        mock_get_provider.return_value = mock_provider

        notif = SMSNotification.objects.create(
            notification_type=NotificationType.APPLICATION_SUBMITTED,
            recipient_phone_masked="******3210",
            status=NotificationStatus.PENDING,
            provider="fast2sms"
        )

        dispatch_sms_notification_task(
            notification_id=str(notif.id),
            phone_number="9876543210",
            message="Your application has been submitted."
        )

        notif.refresh_from_db()
        assert notif.status == NotificationStatus.SENT
        assert notif.provider_request_id == "fast2sms_req_task_1"
        assert notif.sent_at is not None

    @patch("apps.notifications.tasks.get_sms_provider")
    def test_permanent_failure_marks_notification_failed_no_retry(self, mock_get_provider):
        mock_provider = MagicMock()
        mock_provider.send_sms.return_value = SMSProviderResult(
            success=False,
            status='FAILED',
            failure_reason="Invalid mobile number format."
        )
        mock_get_provider.return_value = mock_provider


        notif = SMSNotification.objects.create(
            notification_type=NotificationType.APPLICATION_SUBMITTED,
            recipient_phone_masked="******3210",
            status=NotificationStatus.PENDING,
            provider="fast2sms"
        )

        dispatch_sms_notification_task(
            notification_id=str(notif.id),
            phone_number="9876543210",
            message="Your application has been submitted."
        )

        notif.refresh_from_db()
        assert notif.status == NotificationStatus.FAILED
        assert "Invalid mobile number" in notif.failure_reason


# ==============================================================================
# 5. IDEMPOTENCY & DEDUPLICATION TESTS
# ==============================================================================

@pytest.mark.django_db
class TestNotificationIdempotency:
    @patch("apps.notifications.services.dispatch_sms_notification_task")
    def test_idempotent_submission_prevents_duplicate_sms(self, mock_task):
        # First trigger with idempotency key
        notif1 = NotificationService.send_sms(
            phone_number="9876543210",
            message="Your Tribal Scholar application has been submitted.",
            notification_type=NotificationType.APPLICATION_SUBMITTED,
            idempotency_key="sub:app-idem-001"
        )

        # Duplicate trigger with the same idempotency key
        notif2 = NotificationService.send_sms(
            phone_number="9876543210",
            message="Your Tribal Scholar application has been submitted.",
            notification_type=NotificationType.APPLICATION_SUBMITTED,
            idempotency_key="sub:app-idem-001"
        )

        assert notif1.id == notif2.id
        assert SMSNotification.objects.filter(idempotency_key="sub:app-idem-001").count() == 1


# ==============================================================================
# 6. OTP SERVICE & CRYPTOGRAPHIC SECURITY TESTS
# ==============================================================================

@pytest.mark.django_db
class TestOTPService:
    @patch("apps.notifications.services.secrets.randbelow", return_value=749123)
    def test_otp_generation_and_salted_hashing(self, mock_rand):
        success, msg, masked = OTPService.generate_and_send_otp("9876543210")
        assert success is True
        assert masked == "******3210"

        record = OTPVerification.objects.filter(phone_number="9876543210").first()
        assert record is not None

        # 1. Salted password hash
        assert record.otp_hash != "749123"
        assert check_password("749123", record.otp_hash)

        # 2. Phone must be normalized and masked
        assert record.phone_number == "9876543210"
        assert record.phone_masked == "******3210"

    @patch("apps.notifications.services.secrets.randbelow", return_value=749123)
    def test_successful_otp_verification(self, mock_rand):
        OTPService.generate_and_send_otp("9876543210")

        is_valid, msg, user = OTPService.verify_otp("9876543210", "749123")
        assert is_valid is True

        record = OTPVerification.objects.filter(phone_number="9876543210").first()
        assert record.is_verified is True

    @patch("apps.notifications.services.secrets.randbelow", return_value=749123)
    def test_incorrect_otp_increments_attempts_and_locks_out(self, mock_rand):
        OTPService.generate_and_send_otp("9876543210")

        # Try wrong OTP 5 times (max attempts)
        for _ in range(5):
            is_valid, msg, user = OTPService.verify_otp("9876543210", "000000")
            assert is_valid is False

        record = OTPVerification.objects.filter(phone_number="9876543210").first()
        assert record.attempts >= 5

        # Even the correct OTP must now fail because max attempts is exceeded
        is_valid, msg, user = OTPService.verify_otp("9876543210", "749123")
        assert is_valid is False
        assert "exceeded" in msg.lower()

    @patch("apps.notifications.services.secrets.randbelow", return_value=749123)
    def test_expired_otp_rejected(self, mock_rand):
        OTPService.generate_and_send_otp("9876543210")

        record = OTPVerification.objects.filter(phone_number="9876543210").first()
        # Fast-forward past expiry
        record.expires_at = timezone.now() - timedelta(minutes=1)
        record.save()

        is_valid, msg, user = OTPService.verify_otp("9876543210", "749123")
        assert is_valid is False
        assert "expired" in msg.lower()

    def test_otp_rate_limiting_cooldown(self):
        # First request succeeds
        success1, msg1, _ = OTPService.generate_and_send_otp("9876543210")
        assert success1 is True

        # Second immediate request must be rate-limited
        success2, msg2, _ = OTPService.generate_and_send_otp("9876543210")
        assert success2 is False
        assert "wait" in msg2.lower()

