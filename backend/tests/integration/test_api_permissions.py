import pytest
from rest_framework import status
from apps.schemes.models import Scheme, SchemeType, SchemeVersion, SchemeRule, RuleOperator
from apps.documents.models import SourceDocument, SourceType

@pytest.mark.django_db
def test_applicant_cannot_mutate_scheme_configuration(api_client, applicant_user, admin_user):
    """
    Test 5: Scheme configuration cannot be changed by an applicant.
    Applicants receive HTTP 403 Forbidden on mutations, while admins are authorized.
    """
    doc = SourceDocument.objects.create(
        title="Test Source",
        source_type=SourceType.GUIDELINE,
        academic_year="2025-26",
        checksum="1" * 64,
        content_hash="2" * 64
    )
    scheme = Scheme.objects.create(
        code="MUTATION_TEST",
        name="Scheme Mutation Test",
        scheme_type=SchemeType.FELLOWSHIP
    )
    version = SchemeVersion.objects.create(
        scheme=scheme,
        academic_year="2025-26",
        version_number=1,
        source_document=doc
    )

    # 1. Applicant attempts to create a scheme via API -> HTTP 403
    api_client.force_authenticate(user=applicant_user)
    post_data = {
        "code": "HACKED_SCHEME",
        "name": "Applicant Injected Scheme",
        "description": "Unauthorized scheme",
        "ministry": "Ministry of Tribal Affairs",
        "scheme_type": "SCHOLARSHIP",
        "active": True
    }
    response = api_client.post('/api/v1/schemes/', post_data, format='json')
    assert response.status_code == status.HTTP_403_FORBIDDEN

    # 2. Applicant attempts to update an existing scheme -> HTTP 403
    patch_data = {"name": "Applicant Altered Name"}
    response = api_client.patch(f'/api/v1/schemes/{scheme.id}/', patch_data, format='json')
    assert response.status_code == status.HTTP_403_FORBIDDEN

    # 3. Applicant attempts to add a new rule -> HTTP 403
    rule_data = {
        "scheme_version": str(version.id),
        "rule_code": "APPLICANT_INJECTED_RULE",
        "rule_type": "ELIGIBILITY",
        "field_path": "applicant.community",
        "operator": "EQUALS",
        "value": "ANY",
        "failure_message": "Bypassed rule",
        "source_document": str(doc.id)
    }
    response = api_client.post('/api/v1/rules/', rule_data, format='json')
    assert response.status_code == status.HTTP_403_FORBIDDEN

    # 4. Applicant attempts to delete an existing rule -> HTTP 403
    rule = SchemeRule.objects.create(
        scheme_version=version,
        rule_code="TEST_RULE_DEL",
        field_path="applicant.community",
        operator=RuleOperator.EQUALS,
        value="ST",
        failure_message="ST only",
        source_document=doc
    )
    response = api_client.delete(f'/api/v1/rules/{rule.id}/')
    assert response.status_code == status.HTTP_403_FORBIDDEN

    # 5. Admin executes the same operation -> HTTP 201 Created / HTTP 200 OK
    api_client.force_authenticate(user=admin_user)
    admin_post_data = {
        "code": "ADMIN_SCHEME",
        "name": "Authorized Admin Scheme",
        "description": "Authorized scheme creation",
        "ministry": "Ministry of Tribal Affairs",
        "scheme_type": "SCHOLARSHIP",
        "active": True
    }
    response = api_client.post('/api/v1/schemes/', admin_post_data, format='json')
    assert response.status_code == status.HTTP_201_CREATED
