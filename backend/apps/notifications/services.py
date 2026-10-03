import secrets
import logging
from datetime import timedelta
from typing import Optional, Tuple
from django.db import transaction, IntegrityError
from django.utils import timezone
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password, check_password

from .models import (
    SMSNotification, SMSNotificationType, SMSDeliveryStatus,
    OTPVerification
)
from .templates import render_template
from .providers.fast2sms import normalize_phone_number, mask_phone_number, get_sms_provider
from .tasks import dispatch_sms_notification_task


logger = logging.getLogger(__name__)
User = get_user_model()


class NotificationService:
    """
    Authoritative SMS notification dispatch service for Ministry of Tribal Affairs.
    Guarantees:
    - Bounded asynchronous dispatch via Celery
    - Strict database transaction boundary with transaction.on_commit
    - Idempotency to prevent duplicate transmissions
    - Zero plaintext credential leakage
    """

    @classmethod
    def send_sms(
        cls,
        phone_number: str,
        message: str,
        notification_type: str,
        application=None,
        recipient_user=None,
        idempotency_key: Optional[str] = None,
        force_sync: bool = False
    ) -> SMSNotification:
        """
        Core method to stage, deduplicate, and asynchronously dispatch an SMS notification.
        """
        # 1. Normalize and mask phone number
        norm_phone = normalize_phone_number(phone_number)
        masked_phone = mask_phone_number(norm_phone)

        # 2. Derive deterministic idempotency key if not supplied
        if not idempotency_key:
            app_id = str(application.id) if application else "global"
            idempotency_key = f"{app_id}:{notification_type}:{norm_phone}:{hash(message)}"

        # 3. Check for existing dispatch with same idempotency key (duplicate protection)
        existing = SMSNotification.objects.filter(idempotency_key=idempotency_key).first()
        if existing:
            logger.info(
                "Duplicate SMS suppressed by idempotency key '%s' (status: %s)",
                idempotency_key,
                existing.status
            )
            return existing

        # 4. Create persistent SMSNotification ledger record
        try:
            with transaction.atomic():
                notification = SMSNotification.objects.create(
                    notification_type=notification_type,
                    application=application,
                    recipient_user=recipient_user,
                    recipient_phone_masked=masked_phone,
                    status=SMSDeliveryStatus.PENDING,
                    message_length=len(message),
                    idempotency_key=idempotency_key
                )
        except IntegrityError:
            # Concurrent race caught by database unique constraint
            return SMSNotification.objects.get(idempotency_key=idempotency_key)

        # 5. Dispatch via Celery upon transaction commit (or immediate fallback)
        def trigger_dispatch():
            if force_sync:
                dispatch_sms_notification_task(
                    notification_id=str(notification.id),
                    phone_number=norm_phone,
                    message=message
                )
            else:
                try:
                    dispatch_sms_notification_task.delay(
                        notification_id=str(notification.id),
                        phone_number=norm_phone,
                        message=message
                    )
                except Exception as celery_err:
                    logger.warning(
                        "Celery worker unavailable (%s). Falling back to direct dispatch for %s",
                        celery_err,
                        notification.id
                    )
                    dispatch_sms_notification_task(
                        notification_id=str(notification.id),
                        phone_number=norm_phone,
                        message=message
                    )

        transaction.on_commit(trigger_dispatch)
        return notification

    # -------------------------------------------------------------------------
    # Application-Level Domain Event Notifications
    # -------------------------------------------------------------------------
    @classmethod
    def send_application_submitted(cls, application) -> Optional[SMSNotification]:
        """
        Triggered when applicant completes statutory submission (state -> SUBMITTED).
        """
        phone = cls._resolve_phone(application)
        if not phone:
            return None

        app_num = getattr(application, 'application_number', str(application.id)[:12])
        message = render_template("APPLICATION_SUBMITTED", {"application_id": app_num})
        idempotency_key = f"{application.id}:SUBMITTED:{getattr(application, 'revision_number', 1)}"

        return cls.send_sms(
            phone_number=phone,
            message=message,
            notification_type=SMSNotificationType.APPLICATION_SUBMITTED,
            application=application,
            recipient_user=application.applicant.user if application.applicant else None,
            idempotency_key=idempotency_key
        )

    @classmethod
    def send_verification_completed(cls, application) -> Optional[SMSNotification]:
        """
        Triggered when officer verifies authoritative evidence and eligibility evaluates.
        """
        phone = cls._resolve_phone(application)
        if not phone:
            return None

        app_num = getattr(application, 'application_number', str(application.id)[:12])
        message = render_template("VERIFICATION_COMPLETED", {"application_id": app_num})
        idempotency_key = f"{application.id}:VERIFIED:{getattr(application, 'revision_number', 1)}"

        return cls.send_sms(
            phone_number=phone,
            message=message,
            notification_type=SMSNotificationType.VERIFICATION_COMPLETED,
            application=application,
            recipient_user=application.applicant.user if application.applicant else None,
            idempotency_key=idempotency_key
        )

    @classmethod
    def send_need_more_evidence(cls, application) -> Optional[SMSNotification]:
        """
        Triggered when officer raises a statutory deficiency notice (NEEDS_MORE_EVIDENCE).
        """
        phone = cls._resolve_phone(application)
        if not phone:
            return None

        app_num = getattr(application, 'application_number', str(application.id)[:12])
        message = render_template("NEEDS_MORE_EVIDENCE", {"application_id": app_num})
        idempotency_key = f"{application.id}:DEFICIENCY:{getattr(application, 'revision_number', 1)}"

        return cls.send_sms(
            phone_number=phone,
            message=message,
            notification_type=SMSNotificationType.NEEDS_MORE_EVIDENCE,
            application=application,
            recipient_user=application.applicant.user if application.applicant else None,
            idempotency_key=idempotency_key
        )

    @classmethod
    def send_application_status_changed(cls, application, status_name: str) -> Optional[SMSNotification]:
        """
        Triggered on important state transitions.
        """
        phone = cls._resolve_phone(application)
        if not phone:
            return None

        app_num = getattr(application, 'application_number', str(application.id)[:12])
        message = render_template("APPLICATION_STATUS_CHANGED", {
            "application_id": app_num,
            "status": status_name
        })
        idempotency_key = f"{application.id}:STATUS_{status_name}:{getattr(application, 'revision_number', 1)}"

        return cls.send_sms(
            phone_number=phone,
            message=message,
            notification_type=SMSNotificationType.APPLICATION_STATUS_CHANGED,
            application=application,
            recipient_user=application.applicant.user if application.applicant else None,
            idempotency_key=idempotency_key
        )

    @classmethod
    def send_document_processing_completed(cls, application) -> Optional[SMSNotification]:
        """
        Triggered when document OCR and malware scanning completes.
        """
        phone = cls._resolve_phone(application)
        if not phone:
            return None

        app_num = getattr(application, 'application_number', str(application.id)[:12])
        message = render_template("DOCUMENT_PROCESSING_COMPLETED", {"application_id": app_num})
        idempotency_key = f"{application.id}:DOC_PROCESSED:{getattr(application, 'revision_number', 1)}"

        return cls.send_sms(
            phone_number=phone,
            message=message,
            notification_type=SMSNotificationType.DOCUMENT_PROCESSING_COMPLETED,
            application=application,
            recipient_user=application.applicant.user if application.applicant else None,
            idempotency_key=idempotency_key
        )

    @staticmethod
    def _resolve_phone(application) -> Optional[str]:
        if not application or not application.applicant:
            return None
        user = application.applicant.user
        if not user or not user.phone_number:
            return None
        return user.phone_number


class OTPService:
    """
    Cryptographically secure One-Time Password service.
    Zero plaintext persistence, bounded attempts, rate-limited issuance.
    """

    @classmethod
    def generate_and_send_otp(cls, raw_phone: str) -> Tuple[bool, str, str]:
        """
        Generates a 6-digit cryptographic OTP, stores its salted hash, and sends via Fast2SMS.
        Returns: (success, user_message, masked_phone)
        """
        try:
            norm_phone = normalize_phone_number(raw_phone)
        except ValueError as e:
            return False, str(e), "******"

        masked_phone = mask_phone_number(norm_phone)
        now = timezone.now()

        # 1. Rate limiting: reject if OTP generated within last 60 seconds for this phone
        recent_request = OTPVerification.objects.filter(
            phone_number=norm_phone,
            created_at__gte=now - timedelta(seconds=60)
        ).first()
        if recent_request:
            return False, "An OTP was recently requested. Please wait 60 seconds before retrying.", masked_phone

        # 2. Invalidate previous active OTPs for this number
        OTPVerification.objects.filter(
            phone_number=norm_phone,
            is_verified=False
        ).update(is_verified=True)

        # 3. Generate cryptographically secure 6-digit OTP
        otp_plaintext = f"{secrets.randbelow(1000000):06d}"
        otp_hash = make_password(otp_plaintext)

        expiry_minutes = getattr(settings, 'OTP_EXPIRY_MINUTES', 5)
        expires_at = now + timedelta(minutes=expiry_minutes)

        # Find matching user if already registered
        user = User.objects.filter(phone_number=norm_phone).first()

        # 4. Save hash to database
        OTPVerification.objects.create(
            phone_number=norm_phone,
            phone_masked=masked_phone,
            otp_hash=otp_hash,
            expires_at=expires_at,
            max_attempts=getattr(settings, 'OTP_MAX_ATTEMPTS', 5),
            user=user
        )

        # 5. Format and dispatch SMS
        message = render_template("OTP", {
            "otp": otp_plaintext,
            "expiry_minutes": expiry_minutes
        })

        NotificationService.send_sms(
            phone_number=norm_phone,
            message=message,
            notification_type=SMSNotificationType.OTP,
            recipient_user=user,
            idempotency_key=f"otp:{norm_phone}:{int(now.timestamp())}",
            force_sync=True  # OTP requires immediate dispatch
        )

        return True, "One-Time Password has been dispatched to your mobile number.", masked_phone

    @classmethod
    def verify_otp(cls, raw_phone: str, otp_entered: str) -> Tuple[bool, str, Optional[User]]:
        """
        Verifies entered OTP against stored hash.
        Returns: (is_valid, user_message, user_object_if_any)
        """
        try:
            norm_phone = normalize_phone_number(raw_phone)
        except ValueError:
            return False, "Invalid mobile number format.", None

        if not otp_entered or len(str(otp_entered).strip()) != 6:
            return False, "OTP must be a 6-digit code.", None

        now = timezone.now()
        record = OTPVerification.objects.filter(
            phone_number=norm_phone,
            is_verified=False,
            expires_at__gte=now
        ).order_by('-created_at').first()

        if not record:
            return False, "OTP has expired or is invalid. Please request a new code.", None

        if record.attempts >= record.max_attempts:
            record.is_verified = True  # Invalidate burned record
            record.save(update_fields=['is_verified'])
            return False, "Maximum verification attempts exceeded. Please request a new OTP.", None

        # Increment attempts counter
        record.attempts += 1
        record.save(update_fields=['attempts'])

        # Verify hash
        if check_password(str(otp_entered).strip(), record.otp_hash):
            record.is_verified = True
            record.save(update_fields=['is_verified'])

            # Look up or resolve user
            user = record.user
            if not user:
                user = User.objects.filter(phone_number=norm_phone).first()

            return True, "Verification successful.", user

        remaining = record.max_attempts - record.attempts
        return False, f"Invalid OTP code. {remaining} attempt(s) remaining.", None
