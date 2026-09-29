import pytest
from rest_framework.test import APIClient
from apps.accounts.models import User, UserRole

@pytest.fixture
def api_client():
    return APIClient()

@pytest.fixture
def admin_user(db):
    user = User.objects.create_user(
        username='mota_admin',
        email='admin@tribal.gov.in',
        password='AdminPassword123!',
        role=UserRole.ADMIN,
        is_staff=True
    )
    return user

@pytest.fixture
def applicant_user(db):
    user = User.objects.create_user(
        username='tribal_scholar_applicant',
        email='student@example.org',
        password='StudentPassword123!',
        role=UserRole.APPLICANT
    )
    return user

@pytest.fixture
def scrutiny_officer(db):
    user = User.objects.create_user(
        username='scrutiny_officer_01',
        email='officer@tribal.gov.in',
        password='OfficerPassword123!',
        role=UserRole.SCRUTINY_OFFICER,
        is_staff=True
    )
    return user

@pytest.fixture
def seeded_db(db):
    from django.core.management import call_command
    call_command('seed_schemes')

