import pytest
from django.core.exceptions import ValidationError
from apps.accounts.models import User, UserRole
from apps.schemes.models import Scheme, SchemeType, SchemeVersion
from apps.documents.models import SourceDocument, SourceType
from apps.applicants.models import ApplicantProfile, CommunityCategory
from apps.applications.models import Application
from apps.workflow.models import (
    WorkflowDefinition, WorkflowState, WorkflowTransition, ApplicationStatusHistory
)
from apps.audit.models import AuditLog, AuditAction
from apps.audit.services import log_audit_event

@pytest.fixture
def workflow_setup(db):
    user = User.objects.create_user(username="student_1", role=UserRole.APPLICANT)
    officer = User.objects.create_user(username="officer_1", role=UserRole.SCRUTINY_OFFICER)
    profile = ApplicantProfile.objects.create(user=user, community=CommunityCategory.ST)

    doc = SourceDocument.objects.create(
        title="Test Guideline",
        source_type=SourceType.GUIDELINE,
        academic_year="2025-26",
        checksum="1" * 64,
        content_hash="2" * 64
    )
    scheme = Scheme.objects.create(
        code="WF_TEST",
        name="Workflow Test Scheme",
        scheme_type=SchemeType.FELLOWSHIP
    )
    version = SchemeVersion.objects.create(
        scheme=scheme,
        academic_year="2025-26",
        version_number=1,
        source_document=doc
    )
    wf = WorkflowDefinition.objects.create(
        scheme_version=version,
        name="Standard Workflow"
    )
    s_draft = WorkflowState.objects.create(workflow=wf, code="DRAFT", display_name="Draft", sequence=1)
    s_submitted = WorkflowState.objects.create(workflow=wf, code="SUBMITTED", display_name="Submitted", sequence=2)
    s_scrutiny = WorkflowState.objects.create(workflow=wf, code="UNDER_SCRUTINY", display_name="Under Scrutiny", sequence=3)

    t_submit = WorkflowTransition.objects.create(
        workflow=wf,
        from_state=s_draft,
        to_state=s_submitted,
        required_role="APPLICANT"
    )

    app = Application.objects.create(
        application_number="MOTA/2025/TEST/001",
        applicant=profile,
        scheme_version=version,
        current_state=s_draft
    )
    return {
        "user": user,
        "officer": officer,
        "app": app,
        "s_draft": s_draft,
        "s_submitted": s_submitted,
        "s_scrutiny": s_scrutiny,
        "transition": t_submit
    }


@pytest.mark.django_db
def test_workflow_transitions_are_auditable(workflow_setup):
    """
    Test 4: Workflow transitions generate statutory audit log entries.
    """
    app = workflow_setup["app"]
    s_draft = workflow_setup["s_draft"]
    s_submitted = workflow_setup["s_submitted"]
    officer = workflow_setup["officer"]

    # Record transition in ApplicationStatusHistory
    history_entry = ApplicationStatusHistory.objects.create(
        application=app,
        from_state=s_draft,
        to_state=s_submitted,
        changed_by=officer,
        reason="Dossier submitted by applicant and verified initial documents."
    )

    # Log statutory audit event
    audit_event = log_audit_event(
        entity_type="Application",
        entity_id=str(app.id),
        action=AuditAction.TRANSITION,
        actor=officer,
        actor_role=officer.role,
        before_json={"state": s_draft.code},
        after_json={"state": s_submitted.code},
        reason="Transitioned from DRAFT to SUBMITTED"
    )

    assert history_entry.id is not None
    assert audit_event.id is not None
    assert audit_event.action == AuditAction.TRANSITION
    assert audit_event.entity_id == str(app.id)
    assert audit_event.actor == officer


@pytest.mark.django_db
def test_application_status_history_is_append_only(workflow_setup):
    """
    Test 7: ApplicationStatusHistory is strictly append-only.
    Attempts to update or delete history entries must raise a ValidationError.
    """
    app = workflow_setup["app"]
    s_draft = workflow_setup["s_draft"]
    s_submitted = workflow_setup["s_submitted"]
    user = workflow_setup["user"]

    history_entry = ApplicationStatusHistory.objects.create(
        application=app,
        from_state=s_draft,
        to_state=s_submitted,
        changed_by=user,
        reason="Initial submission"
    )

    # Attempting to mutate an existing history entry must be blocked
    history_entry.reason = "Tampered historical reasoning"
    with pytest.raises(ValidationError, match="immutable and append-only"):
        history_entry.save()

    # Attempting to delete a history entry must be blocked
    with pytest.raises(ValidationError, match="cannot be deleted"):
        history_entry.delete()


@pytest.mark.django_db
def test_audit_log_is_strictly_append_only():
    """
    Verifies that the statutory AuditLog itself cannot be modified or deleted.
    """
    entry = AuditLog.objects.create(
        entity_type="SchemeRule",
        entity_id="rule-uuid-123",
        action=AuditAction.CREATE,
        actor_role="ADMIN",
        reason="Initial rule creation"
    )

    # Attempt mutation
    entry.reason = "Altered audit reason"
    with pytest.raises(ValidationError, match="immutable and append-only"):
        entry.save()

    # Attempt deletion
    with pytest.raises(ValidationError, match="cannot be deleted"):
        entry.delete()

    # Attempt bulk update
    with pytest.raises(ValidationError, match="cannot be modified"):
        AuditLog.objects.filter(id=entry.id).update(reason="Bulk altered")

    # Attempt bulk delete
    with pytest.raises(ValidationError, match="cannot be deleted"):
        AuditLog.objects.filter(id=entry.id).delete()
