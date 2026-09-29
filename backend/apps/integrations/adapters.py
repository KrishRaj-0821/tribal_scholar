from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime

@dataclass
class IntegrationResult:
    """
    Standardized payload returned by government integration adapters.
    """
    success: bool
    service_name: str
    is_mock: bool
    data: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())


class BaseGovernmentAdapter(ABC):
    """
    Abstract interface for government portal integrations.
    Real endpoints require documented production API agreements and certificates.
    Mock implementations are provided for SIH demonstration.
    """
    @abstractmethod
    def verify(self, identifier: str, **kwargs) -> IntegrationResult:
        pass


class MockDigiLockerAdapter(BaseGovernmentAdapter):
    """
    Simulated DigiLocker interface.
    Fetches verified documentary records from synthetic test vault.
    Never calls private/undocumented government endpoints.
    """
    def verify(self, identifier: str, **kwargs) -> IntegrationResult:
        doc_type = kwargs.get('doc_type', 'CASTE_CERTIFICATE')
        return IntegrationResult(
            success=True,
            service_name="DigiLocker Sandbox Mock",
            is_mock=True,
            data={
                "document_uri": f"in.gov.tribal.certificate:{identifier}",
                "doc_type": doc_type,
                "status": "VERIFIED_ISSUER_SIGNATURE",
                "issuer": "District Magistrate / Competent Authority (Simulated)",
                "synthetic_notice": "Student-built SIH Prototype - Synthetic Adapter Response"
            }
        )


class MockAadhaarAdapter(BaseGovernmentAdapter):
    """
    Simulated Aadhaar offline XML/e-KYC verification interface.
    Strictly simulates cryptographic signature check on demographic data.
    Never communicates with live UIDAI endpoints.
    """
    def verify(self, identifier: str, **kwargs) -> IntegrationResult:
        # identifier is masked Aadhaar (e.g. XXXX-XXXX-1234)
        return IntegrationResult(
            success=True,
            service_name="UIDAI Offline e-KYC Mock",
            is_mock=True,
            data={
                "reference_id": f"KYC-SIM-{identifier[-4:]}",
                "demographic_match": True,
                "gender": kwargs.get('gender', 'F'),
                "state": "Odisha (Simulated)",
                "synthetic_notice": "Student-built SIH Prototype - Mock Aadhaar Verification"
            }
        )


class MockPFMSAdapter(BaseGovernmentAdapter):
    """
    Simulated Public Financial Management System (PFMS) adapter.
    Validates DBT bank account beneficiary status and payment readiness.
    """
    def verify(self, identifier: str, **kwargs) -> IntegrationResult:
        return IntegrationResult(
            success=True,
            service_name="PFMS DBT Validation Mock",
            is_mock=True,
            data={
                "account_number_masked": f"XXXXXX{identifier[-4:] if len(identifier) >= 4 else '0000'}",
                "beneficiary_name_status": "MATCHED",
                "dbt_enabled": True,
                "bank_name": "State Bank of India (Simulated)",
                "synthetic_notice": "Student-built SIH Prototype - Mock PFMS Integration"
            }
        )


class MockNSPAdapter(BaseGovernmentAdapter):
    """
    Simulated National Scholarship Portal (NSP) adapter for de-duplication checks.
    """
    def verify(self, identifier: str, **kwargs) -> IntegrationResult:
        return IntegrationResult(
            success=True,
            service_name="NSP De-duplication Mock",
            is_mock=True,
            data={
                "applicant_uid": identifier,
                "has_duplicate_award": False,
                "status": "CLEAR_FOR_SANCTION",
                "synthetic_notice": "Student-built SIH Prototype - Mock NSP Check"
            }
        )


class MockBhashiniAdapter(BaseGovernmentAdapter):
    """
    Simulated BHASHINI language translation adapter for tribal vernaculars.
    """
    def verify(self, identifier: str, **kwargs) -> IntegrationResult:
        source_text = kwargs.get('text', '')
        target_lang = kwargs.get('target_lang', 'sat')  # Santali, Gondi, etc.
        return IntegrationResult(
            success=True,
            service_name="BHASHINI Language Service Mock",
            is_mock=True,
            data={
                "source_text": source_text,
                "target_lang": target_lang,
                "translated_text": f"[Mock {target_lang} Translation]: {source_text}",
                "synthetic_notice": "Student-built SIH Prototype - Mock BHASHINI"
            }
        )
