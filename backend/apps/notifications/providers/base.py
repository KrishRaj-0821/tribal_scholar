from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Dict, Any


@dataclass
class SMSProviderResult:
    """
    Standardized provider execution result across SMS gateways.
    """
    success: bool
    status: str  # 'SENT', 'FAILED', 'RETRY_PENDING', 'DEV_SKIPPED'
    provider_request_id: Optional[str] = None
    message: Optional[str] = None
    failure_reason: Optional[str] = None
    raw_response: Optional[Dict[str, Any]] = None

    @property
    def is_transient_failure(self) -> bool:
        return self.status == 'RETRY_PENDING'



class BaseSMSProvider(ABC):
    """
    Abstract interface for SMS gateway providers.
    """

    @abstractmethod
    def send_sms(self, phone_number: str, message: str, **kwargs) -> SMSProviderResult:
        """
        Sends an SMS message to a single normalized mobile number.
        """
        pass
