import pytest
import uuid
from decimal import Decimal
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status

from apps.applicants.models import ApplicantProfile
from apps.schemes.models import Scheme, SchemeVersion, SchemeType
from apps.applications.models import (
    Application, ApplicationFieldDefinition, ApplicationFieldValue
)
from apps.workflow.models import WorkflowState, WorkflowDefinition
from apps.documents.models import (
    ApplicantDocument, DocumentRequirement, ProvisionalExtractedField,
    ApplicantDocumentType, SourceDocument, SourceType, SourceDocumentStatus
)

User = get_user_model()


@pytest.fixture
def auth_applicant(db):
    user = User.objects.create_user(
        username=f"applicant_test_{uuid.uuid4().hex[:6]}",
        email=f"app_{uuid.uuid4().hex[:6]}@example.com",
        password="ValidPassword123!",
        role="APPLICANT"
    )
    profile = ApplicantProfile.objects.create(
        user=user,
        community="ST",
        annual_family_income=Decimal("450000.00")
    )
    return user, profile


@pytest.fixture
def test_scheme_and_app(db, auth_applicant):
    user, profile = auth_applicant
    scheme = Scheme.objects.create(
        code=f"NOS_TEST_{uuid.uuid4().hex[:4]}",
        name="National Overseas Scholarship Test",
        scheme_type=SchemeType.SCHOLARSHIP,
        active=True
    )
    source_doc = SourceDocument.objects.create(
        title="NOS Official Guidelines Test",
        source_type=SourceType.GUIDELINE,
        academic_year="2025-26",
        checksum="a" * 64,
        content_hash="a" * 64,
        status=SourceDocumentStatus.VERIFIED
    )
    sv = SchemeVersion.objects.create(
        scheme=scheme,
        version_number=1,
        academic_year="2025-26",
        source_document=source_doc,
        status="ACTIVE"
    )
    # Fields
    f_dest = ApplicationFieldDefinition.objects.create(
        scheme_version=sv,
        field_code="study_destination",
        label="Study Destination",
        data_type="SELECT",
        required=True,
        display_order=1,
        validation_schema={"options": ["ABROAD", "DOMESTIC"]}
    )
    f_inc = ApplicationFieldDefinition.objects.create(
        scheme_version=sv,
        field_code="annual_family_income",
        label="Annual Family Income",
        data_type="CURRENCY",
        required=True,
        display_order=2,
        validation_schema={"min": 0, "max": 600000}
    )
    # Requirements
    DocumentRequirement.objects.create(
        scheme_version=sv,
        document_type="INCOME_CERTIFICATE",
        required=True,
        when_required="APPLICATION"
    )
    DocumentRequirement.objects.create(
        scheme_version=sv,
        document_type="ADMISSION_OFFER",
        required=True,
        when_required="APPLICATION"
    )

    wf = WorkflowDefinition.objects.create(
        name="Test Workflow",
        scheme_version=sv,
        active=True
    )
    state_draft = WorkflowState.objects.create(
        workflow=wf,
        code="DRAFT",
        display_name="Draft",
        sequence=1
    )

    app = Application.objects.create(
        applicant=profile,
        scheme_version=sv,
        current_state=state_draft,
        application_number=f"MOTA/2025-26/TEST/{uuid.uuid4().hex[:6]}"
    )
    return user, app, sv


@pytest.mark.django_db
class TestDocumentVaultRegression:
    def test_vault_zero_docs(self, auth_applicant):
        user, _ = auth_applicant
        client = APIClient()
        client.force_authenticate(user=user)

        resp = client.get('/api/v1/documents/vault/')
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data['count'] == 0
        assert resp.data['documents'] == []

    def test_vault_safe_doc(self, auth_applicant):
        user, _ = auth_applicant
        doc = ApplicantDocument.objects.create(
            applicant=user,
            document_type=ApplicantDocumentType.INCOME_CERTIFICATE,
            file_name='income.pdf',
            original_filename='income.pdf',
            storage_key='documents/vault/income.pdf',
            lifecycle_status='SAFE',
            malware_scan_status='CLEAN'
        )

        client = APIClient()
        client.force_authenticate(user=user)
        resp = client.get('/api/v1/documents/vault/')
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data['count'] == 1
        assert resp.data['documents'][0]['id'] == str(doc.id)
        assert resp.data['documents'][0]['security_status'] == 'PASSED'

    def test_vault_ocr_doc(self, auth_applicant):
        user, _ = auth_applicant
        doc = ApplicantDocument.objects.create(
            applicant=user,
            document_type=ApplicantDocumentType.CASTE_CERTIFICATE,
            file_name='caste.pdf',
            original_filename='caste.pdf',
            storage_key='documents/vault/caste.pdf',
            lifecycle_status='PROCESSED',
            malware_scan_status='CLEAN',
            ocr_extracted_text='CERTIFICATE OF SCHEDULED TRIBE'
        )
        ProvisionalExtractedField.objects.create(
            document=doc,
            field_code='caste_certificate_number',
            raw_value='ST/2025/9981',
            confidence=0.98,
            trust_level='OCR_PROVISIONAL'
        )

        client = APIClient()
        client.force_authenticate(user=user)
        resp = client.get('/api/v1/documents/vault/')
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data['count'] == 1
        assert resp.data['documents'][0]['ocr_status'] == 'COMPLETED'
        assert len(resp.data['documents'][0]['extracted_fields']) == 1

    def test_vault_verified_doc(self, auth_applicant):
        user, _ = auth_applicant
        doc = ApplicantDocument.objects.create(
            applicant=user,
            document_type=ApplicantDocumentType.INCOME_CERTIFICATE,
            file_name='income_v.pdf',
            original_filename='income_v.pdf',
            storage_key='documents/vault/income_v.pdf',
            lifecycle_status='VERIFIED',
            malware_scan_status='CLEAN',
            is_verified_by_officer=True
        )

        client = APIClient()
        client.force_authenticate(user=user)
        resp = client.get('/api/v1/documents/vault/')
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data['documents'][0]['verification_status'] == 'VERIFIED'

    def test_vault_mixed_states_resilience(self, auth_applicant):
        user, _ = auth_applicant
        # Safe doc
        ApplicantDocument.objects.create(
            applicant=user, document_type=ApplicantDocumentType.INCOME_CERTIFICATE,
            file_name='d1.pdf', storage_key='k1', lifecycle_status='SAFE'
        )
        # Quarantined doc
        ApplicantDocument.objects.create(
            applicant=user, document_type=ApplicantDocumentType.OTHER,
            file_name='d2.pdf', storage_key='k2', lifecycle_status='QUARANTINED', malware_scan_status='INFECTED'
        )
        # Legacy doc with null original_filename
        ApplicantDocument.objects.create(
            applicant=user, document_type=ApplicantDocumentType.ACADEMIC_TRANSCRIPT,
            file_name='legacy.pdf', original_filename='', storage_key='k3', lifecycle_status='UPLOADED'
        )

        client = APIClient()
        client.force_authenticate(user=user)
        resp = client.get('/api/v1/documents/vault/')
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data['count'] == 3


@pytest.mark.django_db
class TestApplicationFormRegression:
    def test_get_form_schema_200(self, test_scheme_and_app):
        user, app, _ = test_scheme_and_app
        client = APIClient()
        client.force_authenticate(user=user)

        resp = client.get(f'/api/v1/applications/{app.id}/form/')
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data['application_id'] == str(app.id)
        assert 'form' in resp.data
        assert 'effective_values' in resp.data

    def test_patch_partial_draft_save_200(self, test_scheme_and_app):
        user, app, _ = test_scheme_and_app
        client = APIClient()
        client.force_authenticate(user=user)

        # Saving only income (partial draft) without study_destination must succeed with 200
        payload = {
            "answers": {
                "annual_family_income": 450000
            }
        }
        resp = client.patch(f'/api/v1/applications/{app.id}/form/', data=payload, format='json')
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data['status'] == 'SUCCESS'
        assert 'annual_family_income' in resp.data['updated_fields']

    def test_patch_invalid_field_returns_structured_400(self, test_scheme_and_app):
        user, app, _ = test_scheme_and_app
        client = APIClient()
        client.force_authenticate(user=user)

        # Income exceeds 600000 max constraint
        payload = {
            "answers": {
                "annual_family_income": 9999999
            }
        }
        resp = client.patch(f'/api/v1/applications/{app.id}/form/', data=payload, format='json')
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert resp.data['status'] == 'VALIDATION_FAILED'
        assert 'annual_family_income' in resp.data['field_errors']
        assert 'message' in resp.data

    def test_readiness_incomplete_and_complete(self, test_scheme_and_app):
        user, app, sv = test_scheme_and_app
        client = APIClient()
        client.force_authenticate(user=user)

        # Incomplete check
        resp = client.get(f'/api/v1/applications/{app.id}/readiness/')
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data['is_ready'] is False
        assert resp.data['status'] == 'NOT_READY'
        assert 'study_destination' in resp.data['missing_fields']

        # Fill study destination and attach required docs (including ADMISSION_LETTER alias)
        f_dest = ApplicationFieldDefinition.objects.get(scheme_version=sv, field_code='study_destination')
        ApplicationFieldValue.objects.create(
            application=app,
            field_definition=f_dest,
            value_json='ABROAD',
            source='APPLICANT',
            entered_by=user
        )
        f_inc = ApplicationFieldDefinition.objects.get(scheme_version=sv, field_code='annual_family_income')
        ApplicationFieldValue.objects.create(
            application=app,
            field_definition=f_inc,
            value_json=500000,
            source='APPLICANT',
            entered_by=user
        )

        ApplicantDocument.objects.create(
            applicant=user,
            document_type='INCOME_CERTIFICATE',
            file_name='inc.pdf',
            storage_key='k_inc',
            lifecycle_status='SAFE'
        )
        # Using ADMISSION_OFFER requirement
        ApplicantDocument.objects.create(
            applicant=user,
            document_type='ADMISSION_OFFER',
            file_name='adm.pdf',
            storage_key='k_adm',
            lifecycle_status='SAFE'
        )

        resp2 = client.get(f'/api/v1/applications/{app.id}/readiness/')
        assert resp2.status_code == status.HTTP_200_OK
        assert resp2.data['is_ready'] is True
        assert resp2.data['status'] == 'READY'
        assert len(resp2.data['missing_documents']) == 0
        assert len(resp2.data['missing_fields']) == 0
