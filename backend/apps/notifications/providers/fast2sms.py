import re
import logging
from typing import Optional, Dict, Any
import requests
from django.conf import settings

from .base import BaseSMSProvider, SMSProviderResult

logger = logging.getLogger(__name__)


def normalize_phone_number(raw_phone: str) -> str:
    """
    Normalizes an Indian mobile phone number into a 10-digit string.
    Strips country code (+91, 91), leading zeros, spaces, hyphens, and parentheses.
    Validates that the resulting 10-digit number starts with 6, 7, 8, or 9.
    """
    if not raw_phone:
        raise ValueError("Phone number cannot be empty.")

    # Remove all non-digits
    digits = re.sub(r'\D', '', str(raw_phone))

    # Strip country code or leading zeros
    if len(digits) == 12 and digits.startswith('91'):
        digits = digits[2:]
    elif len(digits) == 11 and digits.startswith('0'):
        digits = digits[1:]

    if len(digits) != 10:
        raise ValueError(f"Invalid phone number length ({len(digits)} digits). Must be a 10-digit Indian mobile number.")

    if digits[0] not in ('6', '7', '8', '9'):
        raise ValueError(f"Invalid Indian mobile number: must begin with 6, 7, 8, or 9.")

    return digits


def mask_phone_number(phone: str) -> str:
    """
    Masks a phone number for audit logging and user privacy (e.g. ******4912).
    """
    try:
        norm = normalize_phone_number(phone)
        return f"******{norm[-4:]}"
    except Exception:
        # Fallback if unparseable
        clean = re.sub(r'\D', '', str(phone))
        if len(clean) >= 4:
            return f"{'*' * (len(clean) - 4)}{clean[-4:]}"
        return "******"


PROVIDER_ERROR_MAP: Dict[int, str] = {
    401: "Dev API IP restriction: IP not authorized in Fast2SMS Dev API Security whitelist.",
    412: "Invalid Fast2SMS authorization / API key.",
    413: "Fast2SMS authorization key has been disabled.",
    414: "Dev API IP restriction: IP is blacklisted or not whitelisted in Fast2SMS Dev API Security.",
    416: "Insufficient Fast2SMS wallet balance.",
    424: "Invalid Fast2SMS DLT Message ID.",
    425: "Invalid Fast2SMS DLT Template.",
    500: "Fast2SMS Template or Sender ID blacklisted at DLT.",
    996: "Fast2SMS OTP SMS API requires account KYC completion.",
    999: "Fast2SMS required minimum wallet transaction condition not met.",
}


class Fast2SMSProvider(BaseSMSProvider):
    """
    Authoritative Fast2SMS gateway adapter.
    Supports:
    - Quick SMS (POST https://www.fast2sms.com/dev/bulkV2, route='q')
    - Dedicated OTP SMS (POST https://www.fast2sms.com/dev/otp/send)
    - OTP Resend (POST https://www.fast2sms.com/dev/otp/resend)
    - DLT SMS (POST https://www.fast2sms.com/dev/bulkV2, route='dlt')
    - DLT Manual (route='dlt_manual')
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_url: Optional[str] = None,
        otp_url: Optional[str] = None,
        otp_resend_url: Optional[str] = None,
        otp_template_id: Optional[str] = None,
        sender_id: Optional[str] = None,
        dlt_message_id: Optional[str] = None,
        entity_id: Optional[str] = None,
        route: Optional[str] = None,
        enabled: Optional[bool] = None,
        timeout: Optional[int] = None
    ):
        self.api_key = api_key if api_key is not None else getattr(settings, 'FAST2SMS_API_KEY', '')
        self.api_url = api_url or getattr(settings, 'FAST2SMS_API_URL', 'https://www.fast2sms.com/dev/bulkV2')
        self.otp_url = otp_url or getattr(settings, 'FAST2SMS_OTP_URL', 'https://www.fast2sms.com/dev/otp/send')
        self.otp_resend_url = otp_resend_url or getattr(settings, 'FAST2SMS_OTP_RESEND_URL', 'https://www.fast2sms.com/dev/otp/resend')
        self.otp_template_id = otp_template_id if otp_template_id is not None else getattr(settings, 'FAST2SMS_OTP_TEMPLATE_ID', '')
        self.sender_id = sender_id if sender_id is not None else getattr(settings, 'FAST2SMS_SENDER_ID', '')
        self.dlt_message_id = dlt_message_id if dlt_message_id is not None else getattr(settings, 'FAST2SMS_DLT_MESSAGE_ID', '')
        self.entity_id = entity_id if entity_id is not None else getattr(settings, 'FAST2SMS_ENTITY_ID', '')
        self.route = route or getattr(settings, 'FAST2SMS_ROUTE', 'q')
        self.enabled = enabled if enabled is not None else getattr(settings, 'FAST2SMS_ENABLED', True)
        self.timeout = timeout or getattr(settings, 'FAST2SMS_TIMEOUT_SECONDS', 10)

    def _parse_fast2sms_response(self, response: requests.Response, masked_phone: str) -> SMSProviderResult:
        """
        Parses response from Fast2SMS, handles Fast2SMS return structures,
        and maps error codes (401, 412, 414, 416, 424, 425, 500, 996, 999) to clear diagnoses.
        """
        try:
            resp_json: Dict[str, Any] = response.json()
        except Exception:
            resp_json = {}

        is_return_true = resp_json.get('return') is True or resp_json.get('status_code') == 200
        request_id = str(resp_json.get('request_id', '')) or None
        provider_message = resp_json.get('message')
        if isinstance(provider_message, list):
            provider_message_str = "; ".join(str(m) for m in provider_message)
        else:
            provider_message_str = str(provider_message) if provider_message else response.text

        # Extract Fast2SMS inner status_code if provided
        f2s_code = resp_json.get('status_code')
        try:
            f2s_code_int = int(f2s_code) if f2s_code is not None else response.status_code
        except (ValueError, TypeError):
            f2s_code_int = response.status_code

        diagnosis = PROVIDER_ERROR_MAP.get(f2s_code_int) or PROVIDER_ERROR_MAP.get(response.status_code)

        if response.status_code in (200, 201) and is_return_true:
            logger.info("Fast2SMS dispatch successful to %s (request_id=%s)", masked_phone, request_id)
            return SMSProviderResult(
                success=True,
                status='SENT_TO_PROVIDER',
                provider_request_id=request_id,
                message=provider_message_str,
                raw_response=resp_json
            )
        elif response.status_code in (500, 502, 503, 504) and f2s_code_int not in (401, 412, 413, 414, 416, 424, 425, 996, 999):
            diag_str = f" [{diagnosis}]" if diagnosis else ""
            err_msg = f"Fast2SMS gateway error ({response.status_code}): {provider_message_str}{diag_str}"
            logger.warning("Fast2SMS 5xx gateway error to %s: %s", masked_phone, err_msg)
            return SMSProviderResult(
                success=False,
                status='RETRY_PENDING',
                failure_reason=err_msg,
                raw_response=resp_json
            )
        else:
            diag_str = f" [{diagnosis}]" if diagnosis else ""
            err_msg = f"Fast2SMS rejected dispatch ({f2s_code_int}): {provider_message_str}{diag_str}"
            logger.warning("Fast2SMS rejected dispatch to %s: %s", masked_phone, err_msg)
            return SMSProviderResult(
                success=False,
                status='FAILED',
                failure_reason=err_msg,
                raw_response=resp_json
            )

    def send_sms(self, phone_number: str, message: str, **kwargs) -> SMSProviderResult:
        """
        Sends an SMS via Fast2SMS using the configured route (Quick SMS or DLT).
        """
        try:
            norm_number = normalize_phone_number(phone_number)
        except ValueError as err:
            logger.warning("Fast2SMS recipient validation error: %s", err)
            return SMSProviderResult(
                success=False,
                status='FAILED',
                failure_reason=str(err)
            )

        masked_phone = mask_phone_number(norm_number)

        if not self.enabled:
            logger.info(
                "[DEV_MODE] Fast2SMS is disabled (FAST2SMS_ENABLED=false). "
                "Simulating dispatch to %s: '%s'",
                masked_phone,
                message[:60] + "..." if len(message) > 60 else message
            )
            return SMSProviderResult(
                success=True,
                status='DEV_SKIPPED',
                provider_request_id='DEV_MODE_MOCK_DISPATCH',
                message='Fast2SMS dispatch skipped in development mode (FAST2SMS_ENABLED=false).'
            )

        if not self.api_key:
            err_msg = "FAST2SMS_API_KEY is not configured in backend/worker environment."
            logger.error("Fast2SMS configuration error: %s", err_msg)
            return SMSProviderResult(
                success=False,
                status='FAILED',
                failure_reason=err_msg
            )

        headers = {
            'authorization': self.api_key,
            'Authorization': self.api_key,
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        }

        # Build payload according to route
        target_route = kwargs.get('route') or self.route
        if target_route == 'dlt':
            sender = kwargs.get('sender_id') or self.sender_id
            msg_id = kwargs.get('message_id') or self.dlt_message_id
            if not sender or not msg_id:
                err_msg = "DLT route requires valid sender_id (FAST2SMS_SENDER_ID) and message ID (FAST2SMS_DLT_MESSAGE_ID)."
                logger.error("Fast2SMS DLT configuration incomplete: %s", err_msg)
                return SMSProviderResult(success=False, status='FAILED', failure_reason=err_msg)
            payload = {
                'route': 'dlt',
                'sender_id': sender,
                'message': msg_id,
                'variables_values': kwargs.get('variables_values', ''),
                'numbers': norm_number,
            }
        elif target_route == 'dlt_manual':
            payload = {
                'route': 'dlt_manual',
                'requests': [{
                    'sender_id': kwargs.get('sender_id') or self.sender_id,
                    'entity_id': kwargs.get('entity_id') or self.entity_id,
                    'template_id': kwargs.get('template_id') or self.dlt_message_id,
                    'message': message,
                    'flash': 0,
                    'numbers': norm_number,
                }]
            }
        else:
            # Default: route='q' (Quick SMS)
            payload = {
                'route': 'q',
                'message': message,
                'numbers': norm_number,
            }

        logger.info(
            "Dispatching Fast2SMS to recipient %s (length: %d chars, route: %s, endpoint: %s)",
            masked_phone,
            len(message),
            target_route,
            self.api_url
        )

        try:
            response = requests.post(
                self.api_url,
                json=payload,
                headers=headers,
                timeout=self.timeout
            )
            return self._parse_fast2sms_response(response, masked_phone)
        except (requests.ConnectionError, requests.Timeout) as net_err:
            logger.warning("Fast2SMS network connectivity error: %s", type(net_err).__name__)
            return SMSProviderResult(
                success=False,
                status='RETRY_PENDING',
                failure_reason=f"Network error contacting Fast2SMS: {type(net_err).__name__}"
            )
        except requests.RequestException as req_err:
            logger.error("Fast2SMS request error: %s", req_err)
            return SMSProviderResult(
                success=False,
                status='FAILED',
                failure_reason=f"HTTP request error: {str(req_err)}"
            )

    def send_otp(
        self,
        phone_number: str,
        otp_code: str,
        expiry_minutes: int = 5,
        **kwargs
    ) -> SMSProviderResult:
        """
        Sends an OTP using Fast2SMS dedicated OTP API (POST /dev/otp/send) if configured,
        or falls back to Quick SMS route.
        """
        try:
            norm_number = normalize_phone_number(phone_number)
        except ValueError as err:
            logger.warning("Fast2SMS OTP recipient validation error: %s", err)
            return SMSProviderResult(success=False, status='FAILED', failure_reason=str(err))

        masked_phone = mask_phone_number(norm_number)

        if not self.enabled:
            logger.info("[DEV_MODE] Fast2SMS disabled. Simulating OTP dispatch to %s", masked_phone)
            return SMSProviderResult(
                success=True,
                status='DEV_SKIPPED',
                provider_request_id='DEV_MODE_MOCK_DISPATCH',
                message='Fast2SMS dispatch skipped in development mode (FAST2SMS_ENABLED=false).'
            )

        if not self.api_key:
            err_msg = "FAST2SMS_API_KEY is not configured in backend/worker environment."
            logger.error("Fast2SMS configuration error: %s", err_msg)
            return SMSProviderResult(success=False, status='FAILED', failure_reason=err_msg)

        headers = {
            'authorization': self.api_key,
            'Authorization': self.api_key,
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        }

        # If dedicated OTP template ID is configured, dispatch via POST /dev/otp/send
        if self.otp_template_id:
            payload = {
                'mobile': norm_number,
                'otp_id': self.otp_template_id,
                'otp': otp_code,
                'otp_length': len(otp_code),
                'otp_expiry': expiry_minutes,
            }
            if kwargs.get('variables_values'):
                payload['variables_values'] = kwargs['variables_values']

            logger.info(
                "Dispatching Fast2SMS Dedicated OTP to %s via %s (otp_id=%s)",
                masked_phone,
                self.otp_url,
                self.otp_template_id
            )
            try:
                response = requests.post(self.otp_url, json=payload, headers=headers, timeout=self.timeout)
                return self._parse_fast2sms_response(response, masked_phone)
            except (requests.ConnectionError, requests.Timeout) as net_err:
                logger.warning("Fast2SMS network connectivity error: %s", type(net_err).__name__)
                return SMSProviderResult(
                    success=False,
                    status='RETRY_PENDING',
                    failure_reason=f"Network error contacting Fast2SMS: {type(net_err).__name__}"
                )
            except requests.RequestException as req_err:
                logger.error("Fast2SMS request error: %s", req_err)
                return SMSProviderResult(
                    success=False,
                    status='FAILED',
                    failure_reason=f"HTTP request error: {str(req_err)}"
                )
        else:
            # Fallback to Quick SMS route with statutory template
            msg = kwargs.pop('message', None) or f"Your Tribal Scholar verification OTP is {otp_code}. It expires in {expiry_minutes} minutes."
            logger.info("FAST2SMS_OTP_TEMPLATE_ID not configured; dispatching OTP via SMS route '%s' to %s", self.route, masked_phone)
            return self.send_sms(phone_number=norm_number, message=msg, **kwargs)

    def resend_otp(self, phone_number: str) -> SMSProviderResult:
        """
        Calls Fast2SMS dedicated resend endpoint (POST /dev/otp/resend).
        """
        try:
            norm_number = normalize_phone_number(phone_number)
        except ValueError as err:
            return SMSProviderResult(success=False, status='FAILED', failure_reason=str(err))

        masked_phone = mask_phone_number(norm_number)
        if not self.enabled:
            return SMSProviderResult(success=True, status='DEV_SKIPPED', message='Dev mode mock resend.')
        if not self.api_key:
            return SMSProviderResult(success=False, status='FAILED', failure_reason='FAST2SMS_API_KEY missing.')

        headers = {
            'authorization': self.api_key,
            'Authorization': self.api_key,
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        }
        payload = {'mobile': norm_number}
        logger.info("Calling Fast2SMS OTP Resend for %s via %s", masked_phone, self.otp_resend_url)
        try:
            response = requests.post(self.otp_resend_url, json=payload, headers=headers, timeout=self.timeout)
            return self._parse_fast2sms_response(response, masked_phone)
        except Exception as e:
            return SMSProviderResult(success=False, status='FAILED', failure_reason=str(e))


def get_sms_provider() -> Fast2SMSProvider:
    """
    Returns an instance of the configured SMS provider.
    """
    return Fast2SMSProvider()

