from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from .adapters import (
    MockDigiLockerAdapter, MockAadhaarAdapter, MockPFMSAdapter,
    MockNSPAdapter, MockBhashiniAdapter
)

class IntegrationStatusView(APIView):
    """
    Status view exposing registered government interface adapters and their sandbox mock status.
    Conforms to SIH prototype guidelines: no scraping, no fake production endpoints.
    """
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({
            "system": "MoTA Tribal Scholar Management Platform",
            "prototype_status": "SIH Student Prototype - Sandboxed Mock Adapters",
            "adapters": [
                {
                    "name": "DigiLocker",
                    "mode": "Sandbox Mock Interface",
                    "live_endpoint_claimed": False,
                    "supported_docs": ["CASTE_CERTIFICATE", "INCOME_CERTIFICATE", "MARKSHEET"]
                },
                {
                    "name": "UIDAI Aadhaar e-KYC",
                    "mode": "Offline XML Demographic Mock",
                    "live_endpoint_claimed": False,
                    "supported_methods": ["Demographic Match", "Masked UID"]
                },
                {
                    "name": "PFMS",
                    "mode": "DBT Validation Sandbox Mock",
                    "live_endpoint_claimed": False,
                    "supported_methods": ["Beneficiary Name Match", "Account Active Check"]
                },
                {
                    "name": "NSP (National Scholarship Portal)",
                    "mode": "De-duplication Mock",
                    "live_endpoint_claimed": False,
                    "supported_methods": ["Scholarship Duplication Screening"]
                },
                {
                    "name": "BHASHINI",
                    "mode": "Tribal Vernacular Translation Sandbox Mock",
                    "live_endpoint_claimed": False,
                    "supported_languages": ["Santali", "Gondi", "Bodo", "Hindi", "English"]
                },
            ]
        })
