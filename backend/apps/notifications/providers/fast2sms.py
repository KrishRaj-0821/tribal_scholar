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


class Fast2SMSProvider(BaseSMSProvider):
    """
    Authoritative Fast2SMS Quick SMS gateway adapter.
    Uses POST https://www.fast2sms.com/dev/bulkV2 with JSON body.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_url: Optional[str] = None,
        route: Optional[str] = None,
        enabled: Optional[bool] = None,
        timeout: Optional[int] = None
    ):
        self.api_key = api_key if api_key is not None else getattr(settings, 'FAST2SMS_API_KEY', '')
        self.api_url = api_url or getattr(settings, 'FAST2SMS_API_URL', 'https://www.fast2sms.com/dev/bulkV2')
        self.route = route or getattr(settings, 'FAST2SMS_ROUTE', 'q')
        self.enabled = enabled if enabled is not None else getattr(settings, 'FAST2SMS_ENABLED', True)
        self.timeout = timeout or getattr(settings, 'FAST2SMS_TIMEOUT_SECONDS', 10)

    def send_sms(self, phone_number: str, message: str, **kwargs) -> SMSProviderResult:
        """
        Sends an SMS via Fast2SMS Quick SMS API.
        """
        # 1. Normalize recipient number
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

        # 2. Check if provider is enabled
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

        # 3. Check API key configuration
        if not self.api_key:
            err_msg = "FAST2SMS_API_KEY is not configured in backend/worker environment."
            logger.error("Fast2SMS configuration error: %s", err_msg)
            return SMSProviderResult(
                success=False,
                status='FAILED',
                failure_reason=err_msg
            )

        # 4. Construct HTTP request
        headers = {
            'authorization': self.api_key,
            'Authorization': self.api_key,
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        }

        payload = {
            'route': self.route,
            'message': message,
            'numbers': norm_number,
        }

        logger.info(
            "Dispatching Fast2SMS Quick SMS to recipient %s (length: %d chars, route: %s)",
            masked_phone,
            len(message),
            self.route
        )

        try:
            response = requests.post(
                self.api_url,
                json=payload,
                headers=headers,
                timeout=self.timeout
            )
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

        # 5. Parse response
        try:
            resp_json: Dict[str, Any] = response.json()
        except Exception:
            resp_json = {}

        # Fast2SMS returns:
        # Success: {"return": true, "request_id": "v35b3678h8...", "message": ["SMS sent successfully."]}
        # Failure: {"return": false, "status_code": 400, "message": "..."}
        is_return_true = resp_json.get('return') is True or resp_json.get('status_code') == 200
        request_id = str(resp_json.get('request_id', '')) or None
        provider_message = resp_json.get('message')
        if isinstance(provider_message, list):
            provider_message_str = "; ".join(str(m) for m in provider_message)
        else:
            provider_message_str = str(provider_message) if provider_message else response.text

        if response.status_code in (200, 201) and is_return_true:
            logger.info("Fast2SMS dispatch successful to %s (request_id=%s)", masked_phone, request_id)
            return SMSProviderResult(
                success=True,
                status='SENT_TO_PROVIDER',
                provider_request_id=request_id,
                message=provider_message_str,
                raw_response=resp_json
            )
        elif response.status_code in (500, 502, 503, 504):

            # Transient 5xx server error -> candidate for bounded retry
            logger.warning("Fast2SMS 5xx gateway error (%d): %s", response.status_code, provider_message_str)
            return SMSProviderResult(
                success=False,
                status='RETRY_PENDING',
                failure_reason=f"Fast2SMS gateway error ({response.status_code}): {provider_message_str}",
                raw_response=resp_json
            )
        else:
            # Permanent client/auth/validation rejection
            logger.warning("Fast2SMS rejected dispatch (%d): %s", response.status_code, provider_message_str)
            return SMSProviderResult(
                success=False,
                status='FAILED',
                failure_reason=f"Fast2SMS rejected ({response.status_code}): {provider_message_str}",
                raw_response=resp_json
            )


def get_sms_provider() -> Fast2SMSProvider:
    """
    Returns an instance of the configured SMS provider.
    """
    return Fast2SMSProvider()

