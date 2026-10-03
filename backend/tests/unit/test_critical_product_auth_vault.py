import pytest
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from apps.accounts.models import UserRole
from apps.applicants.models import ApplicantProfile, CommunityCategory
from apps.documents.models import ApplicantDocument, ApplicantDocumentType, DocumentLifecycleStatus

User = get_user_model()


@pytest.mark.django_db
class TestCriticalProductSecurityAndVault:
    def setup_method(self):
        self.client = APIClient()

    def test_anonymous_cannot_access_profile(self):
        response = self.client.get('/api/v1/applicants/profile/')
        assert response.status_code in [401, 403]

    def test_anonymous_cannot_access_vault(self):
        response = self.client.get('/api/v1/documents/vault/')
        assert response.status_code in [401, 403]

    def test_public_registration_forces_applicant_role(self):
        # Even if payload tries to escalate to SCRUTINY_OFFICER or ADMIN
        payload = {
            "username": "test_public_user_99",
            "email": "test_public_user_99@tribal.nic.in",
            "password": "ValidPassword@2026!",
            "first_name": "Kishu",
            "last_name": "Raj",
            "phone_number": "9876543210",
            "role": "SCRUTINY_OFFICER"
        }
        response = self.client.post('/api/v1/auth/register/', payload, format='json')
        assert response.status_code == 201
        
        user = User.objects.get(username="test_public_user_99")
        assert user.role == UserRole.APPLICANT
        assert not user.is_staff
        assert not user.is_superuser

    def test_applicant_cannot_access_officer_queue(self):
        user = User.objects.create_user(
            username="test_applicant_rb",
            email="test_applicant_rb@tribal.nic.in",
            password="TribalPassword@2026",
            role=UserRole.APPLICANT
        )
        self.client.force_authenticate(user=user)
        response = self.client.get('/api/v1/verification/queue/')
        assert response.status_code == 403

    def test_officer_can_access_officer_queue(self):
        officer = User.objects.create_user(
            username="test_officer_rb",
            email="test_officer_rb@tribal.nic.in",
            password="OfficerPassword@2026",
            role=UserRole.SCRUTINY_OFFICER
        )
        self.client.force_authenticate(user=officer)
        response = self.client.get('/api/v1/verification/queue/')
        assert response.status_code == 200

    def test_applicant_vault_crud_and_reusable_fields(self):
        user = User.objects.create_user(
            username="vault_test_user",
            email="vault_test_user@tribal.nic.in",
            password="TribalPassword@2026",
            role=UserRole.APPLICANT
        )
        profile = ApplicantProfile.objects.create(
            user=user,
            community=CommunityCategory.ST,
            annual_family_income=450000.00
        )
        self.client.force_authenticate(user=user)

        # 1. Fetch empty vault
        res = self.client.get('/api/v1/documents/vault/')
        assert res.status_code == 200
        assert res.data['title'] == 'MY DOCUMENT VAULT'
        assert res.data['documents'] == []

        # 2. Fetch reusable fields
        res_reusable = self.client.get('/api/v1/documents/vault/reusable-fields/')
        assert res_reusable.status_code == 200
        data = res_reusable.data
        assert 'community' in data
        assert data['community']['value'] == 'ST'
        assert float(data['annual_family_income']['value']) == 450000.0
