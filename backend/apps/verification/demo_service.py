import uuid
import hashlib
from typing import Dict, Any
from django.db import transaction
from django.utils import timezone
from django.contrib.auth import get_user_model

from apps.accounts.models import UserRole
from apps.applicants.models import ApplicantProfile, CommunityCategory
from apps.schemes.models import Scheme, SchemeVersion, SchemeRule
from apps.applications.models import (
    Application, ApplicationFieldValue, ApplicationFieldDefinition,
    FieldConflict, FieldValueSource
)
from apps.documents.models import (
    ApplicantDocument, DocumentLifecycleStatus, ApplicantDocumentType,
    OCRResult, OCRPage, OCRBlock, ProvisionalExtractedField
)
from apps.workflow.models import WorkflowState
from apps.verification.models import (
    VerificationQueueItem, VerificationStatus, VerificationPriority,
    VerificationItemType, DocumentVerificationRecord
)
from apps.schemes.evaluator import RuleEvaluationService

User = get_user_model()

DEMO_APPLICATION_NUMBER = "APP-2026-001DB3"
DEMO_APPLICANT_USERNAME = "demo_applicant"
DEMO_OFFICER_USERNAME = "demo_officer"


class DemoScenarioService:
    """
    Seeds and resets the deterministic SIH demo scenario:
    - Candidate: Demo ST Applicant (Mandla, MP)
    - Declared Income: ₹5,00,000 (APPLICANT_DECLARED, Rank 20)
    - OCR Extracted Income: ₹4,50,000 (OCR_PROVISIONAL, Rank 10)
    - Conflict: MATERIAL_CONFLICT
    - Queue Status: PENDING (High Priority)
    """

    @classmethod
    @transaction.atomic
    def reset_demo_scenario(cls) -> Dict[str, Any]:
        """
        Idempotently wipes and re-seeds the demo scenario.
        """
        # 1. Clean up existing demo records if present using raw SQL (bypasses immutable audit block)
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("""
                DELETE FROM verification_documentverificationrecord 
                WHERE document_id IN (
                    SELECT d.id FROM documents_applicantdocument d 
                    JOIN applications_application a ON d.application_id = a.id 
                    WHERE a.application_number = %s
                )
            """, [DEMO_APPLICATION_NUMBER])
            cursor.execute("""
                DELETE FROM applications_eligibilityinputsnapshot
                WHERE evaluation_id IN (
                    SELECT e.id FROM applications_eligibilityevaluation e
                    JOIN applications_application a ON e.application_id = a.id
                    WHERE a.application_number = %s
                )
            """, [DEMO_APPLICATION_NUMBER])
            cursor.execute("""
                DELETE FROM applications_eligibilityevaluation 
                WHERE application_id IN (
                    SELECT a.id FROM applications_application a 
                    WHERE a.application_number = %s
                )
            """, [DEMO_APPLICATION_NUMBER])
            cursor.execute("""
                DELETE FROM verification_verificationqueueitem 
                WHERE application_id IN (
                    SELECT a.id FROM applications_application a 
                    WHERE a.application_number = %s
                )
            """, [DEMO_APPLICATION_NUMBER])
            cursor.execute("""
                DELETE FROM applications_fieldconflict 
                WHERE application_id IN (
                    SELECT a.id FROM applications_application a 
                    WHERE a.application_number = %s
                )
            """, [DEMO_APPLICATION_NUMBER])
            cursor.execute("""
                DELETE FROM documents_provisionalextractedfield 
                WHERE document_id IN (
                    SELECT d.id FROM documents_applicantdocument d 
                    JOIN applications_application a ON d.application_id = a.id 
                    WHERE a.application_number = %s
                )
            """, [DEMO_APPLICATION_NUMBER])
            cursor.execute("""
                DELETE FROM documents_ocrblock 
                WHERE page_id IN (
                    SELECT p.id FROM documents_ocrpage p 
                    JOIN documents_ocrresult r ON p.ocr_result_id = r.id 
                    JOIN documents_applicantdocument d ON r.document_id = d.id 
                    JOIN applications_application a ON d.application_id = a.id 
                    WHERE a.application_number = %s
                )
            """, [DEMO_APPLICATION_NUMBER])
            cursor.execute("""
                DELETE FROM documents_ocrpage 
                WHERE ocr_result_id IN (
                    SELECT r.id FROM documents_ocrresult r 
                    JOIN documents_applicantdocument d ON r.document_id = d.id 
                    JOIN applications_application a ON d.application_id = a.id 
                    WHERE a.application_number = %s
                )
            """, [DEMO_APPLICATION_NUMBER])
            cursor.execute("""
                DELETE FROM documents_ocrresult 
                WHERE document_id IN (
                    SELECT d.id FROM documents_applicantdocument d 
                    JOIN applications_application a ON d.application_id = a.id 
                    WHERE a.application_number = %s
                )
            """, [DEMO_APPLICATION_NUMBER])
            cursor.execute("""
                DELETE FROM documents_ocrjob 
                WHERE document_id IN (
                    SELECT d.id FROM documents_applicantdocument d 
                    JOIN applications_application a ON d.application_id = a.id 
                    WHERE a.application_number = %s
                )
            """, [DEMO_APPLICATION_NUMBER])
            cursor.execute("""
                DELETE FROM documents_applicantdocument 
                WHERE application_id IN (
                    SELECT a.id FROM applications_application a 
                    WHERE a.application_number = %s
                )
            """, [DEMO_APPLICATION_NUMBER])
            cursor.execute("""
                DELETE FROM applications_applicationfieldvalue 
                WHERE application_id IN (
                    SELECT a.id FROM applications_application a 
                    WHERE a.application_number = %s
                )
            """, [DEMO_APPLICATION_NUMBER])
            cursor.execute("""
                DELETE FROM applications_application 
                WHERE application_number = %s
            """, [DEMO_APPLICATION_NUMBER])

        # 2. Seed Demo Applicant User & Profile
        applicant_user, _ = User.objects.get_or_create(
            username=DEMO_APPLICANT_USERNAME,
            defaults={
                "first_name": "Demo ST",
                "last_name": "Applicant",
                "email": "demo.applicant@mota.gov.in",
                "role": UserRole.APPLICANT,
                "is_verified": True
            }
        )
        if applicant_user.role != UserRole.APPLICANT:
            applicant_user.role = UserRole.APPLICANT
            applicant_user.save()

        applicant_profile, _ = ApplicantProfile.objects.get_or_create(
            user=applicant_user,
            defaults={
                "community": CommunityCategory.ST,
                "annual_family_income": 500000.00,
                "is_synthetic": True,
                "gender": "FEMALE"
            }
        )
        applicant_profile.annual_family_income = 500000.00
        applicant_profile.save()

        # 3. Seed Demo Scrutiny Officer User
        officer_user, _ = User.objects.get_or_create(
            username=DEMO_OFFICER_USERNAME,
            defaults={
                "first_name": "Shri S. K.",
                "last_name": "Mahapatra",
                "email": "officer.mandla@mota.gov.in",
                "role": UserRole.SCRUTINY_OFFICER,
                "is_staff": True,
                "is_verified": True
            }
        )
        if officer_user.role != UserRole.SCRUTINY_OFFICER:
            officer_user.role = UserRole.SCRUTINY_OFFICER
            officer_user.save()

        # 4. Target SchemeVersion
        scheme_version = SchemeVersion.objects.filter(
            scheme__code__in=['TOP_CLASS', 'TOP-05', 'NFST']
        ).first()

        if not scheme_version:
            scheme, _ = Scheme.objects.get_or_create(
                code="TOP-05",
                defaults={"name": "Top Class Education for ST Students", "short_name": "Top Class"}
            )
            scheme_version = SchemeVersion.objects.create(
                scheme=scheme,
                academic_year="2026-27",
                version_number=1,
                status="ACTIVE"
            )

        # 5. Workflow State
        workflow_state = WorkflowState.objects.filter(code='UNDER_SCRUTINY').first()
        if not workflow_state:
            workflow_state = WorkflowState.objects.first()

        # 6. Create Demo Application
        demo_app = Application.objects.create(
            application_number=DEMO_APPLICATION_NUMBER,
            applicant=applicant_profile,
            scheme_version=scheme_version,
            current_state=workflow_state,
            is_synthetic=True,
            submission_data_json={
                "full_name": "Demo ST Applicant",
                "category": "ST",
                "state": "Madhya Pradesh",
                "district": "Mandla",
                "annual_family_income": 500000,
                "institution_name": "Synthetic Demo University",
                "institute_code": "IIT_INDORE",
                "course": "Postgraduate (M.Tech Computer Science)",
                "academic_year": "2026-27"
            }
        )

        # 7. Create Application Field Values (Declared values: Rank 20)
        field_def_income = ApplicationFieldDefinition.objects.filter(
            scheme_version=scheme_version, field_code='annual_family_income'
        ).first()

        if field_def_income:
            ApplicationFieldValue.objects.create(
                application=demo_app,
                field_definition=field_def_income,
                value_json=500000,
                source=FieldValueSource.APPLICANT_DECLARED
            )

        # 8. Create Demo Document (SAFE income certificate)
        doc_hash = hashlib.sha256(b"DEMO_INCOME_CERT_2026_MANDLA").hexdigest()
        doc = ApplicantDocument.objects.create(
            applicant=applicant_user,
            application=demo_app,
            document_type=ApplicantDocumentType.INCOME_CERTIFICATE,
            file_name="income_cert_mandla_2026.png",
            original_filename="income_cert_mandla_2026.png",
            storage_key="safe/income_cert_mandla_2026.png",
            file_size_bytes=248912,
            detected_mime_type="image/png",
            lifecycle_status=DocumentLifecycleStatus.SAFE,
            sha256=doc_hash,
            checksum=doc_hash,
            is_verified_by_officer=False
        )

        # 9. Create OCR Job, OCR Result & Provisional Blocks
        from apps.documents.models import OCRJob, OCRJobStatus
        ocr_job = OCRJob.objects.create(
            document=doc,
            status=OCRJobStatus.COMPLETED,
            idempotency_key=f"DEMO-OCR-{doc.id}",
            engine_name="PaddleOCR",
            engine_version="3.7.0",
            pipeline_version="1.0.0"
        )

        ocr_text = (
            "भारत सरकार / GOVERNMENT OF INDIA\n"
            "आय प्रमाण पत्र (INCOME CERTIFICATE)\n"
            "कार्यालय अनुमंडल पदाधिकारी / तहसीलदार, मंडला (मध्य प्रदेश)\n"
            "प्रमाण पत्र संख्या: TEST-2026-001\n"
            "आवेदक का नाम: Demo ST Applicant\n"
            "समुदाय: अनुसूचित जनजाति (ST)\n"
            "वार्षिक पारिवारिक आय: 450000 रुपये (रुपये चार लाख पचास हजार मात्र)\n"
            "जारी करने का दिनांक: 15/01/2026\n"
            "हस्ताक्षर एवं मुहर: तहसीलदार, मंडला"
        )
        ocr_res = OCRResult.objects.create(
            ocr_job=ocr_job,
            document=doc,
            page_count=1,
            engine_name="PaddleOCR",
            engine_version="3.7.0",
            pipeline_version="1.0.0",
            result_hash=hashlib.sha256(ocr_text.encode('utf-8')).hexdigest(),
            full_text=ocr_text
        )

        ocr_page = OCRPage.objects.create(
            ocr_result=ocr_res,
            page_number=1,
            width=1000,
            height=1414,
            page_hash=hashlib.sha256(b"PAGE_1").hexdigest(),
            page_confidence=0.96
        )

        block_income = OCRBlock.objects.create(
            page=ocr_page,
            extracted_text="वार्षिक पारिवारिक आय: 450000 रुपये",
            confidence=0.94,
            bbox_x=150,
            bbox_y=680,
            bbox_width=700,
            bbox_height=60,
            language="hi",
            reading_order=5
        )

        block_cert = OCRBlock.objects.create(
            page=ocr_page,
            extracted_text="प्रमाण पत्र संख्या: TEST-2026-001",
            confidence=0.98,
            bbox_x=150,
            bbox_y=420,
            bbox_width=650,
            bbox_height=55,
            language="hi",
            reading_order=3
        )

        block_dist = OCRBlock.objects.create(
            page=ocr_page,
            extracted_text="कार्यालय तहसीलदार, मंडला (मध्य प्रदेश)",
            confidence=0.95,
            bbox_x=150,
            bbox_y=300,
            bbox_width=700,
            bbox_height=55,
            language="hi",
            reading_order=2
        )

        # 10. Provisional Extracted Fields (Rank 10)
        ProvisionalExtractedField.objects.create(
            document=doc,
            ocr_result=ocr_res,
            ocr_page=ocr_page,
            ocr_block=block_income,
            field_code="annual_family_income",
            field_label="Annual Family Income",
            raw_value="450000",
            normalized_value=450000,
            confidence=0.94,
            trust_level="OCR_PROVISIONAL",
            page_number=1,
            bounding_box={"x": 15, "y": 48, "width": 70, "height": 6}
        )

        ProvisionalExtractedField.objects.create(
            document=doc,
            ocr_result=ocr_res,
            ocr_page=ocr_page,
            ocr_block=block_cert,
            field_code="certificate_number",
            field_label="Certificate Number",
            raw_value="TEST-2026-001",
            normalized_value="TEST-2026-001",
            confidence=0.98,
            trust_level="OCR_PROVISIONAL",
            page_number=1,
            bounding_box={"x": 15, "y": 30, "width": 65, "height": 5}
        )

        ProvisionalExtractedField.objects.create(
            document=doc,
            ocr_result=ocr_res,
            ocr_page=ocr_page,
            ocr_block=block_dist,
            field_code="state",
            field_label="State",
            raw_value="MADHYA PRADESH",
            normalized_value="MADHYA PRADESH",
            confidence=0.96,
            trust_level="OCR_PROVISIONAL",
            page_number=1
        )

        ProvisionalExtractedField.objects.create(
            document=doc,
            ocr_result=ocr_res,
            ocr_page=ocr_page,
            ocr_block=block_dist,
            field_code="district",
            field_label="District",
            raw_value="MANDLA",
            normalized_value="MANDLA",
            confidence=0.95,
            trust_level="OCR_PROVISIONAL",
            page_number=1
        )

        # 11. Create Real Material Conflict Record
        conflict = FieldConflict.objects.create(
            application=demo_app,
            field_code="annual_family_income",
            values_json={"declared": 500000, "extracted": 450000},
            source_values={"declared": "APPLICANT_DECLARED", "extracted": "OCR_PROVISIONAL"},
            status="OPEN",
            severity="HIGH"
        )

        # 12. Create Verification Queue Item (HIGH Priority, PENDING)
        queue_item = VerificationQueueItem.objects.create(
            application=demo_app,
            document=doc,
            item_type=VerificationItemType.DOCUMENT,
            target_identifier="annual_family_income",
            priority=VerificationPriority.HIGH,
            status=VerificationStatus.PENDING,
            conflict_type="MATERIAL_CONFLICT",
            confidence_score=0.94,
            officer_remarks="Income Conflict: Declared ₹5,00,000 vs Certificate ₹4,50,000",
            current_evidence_json={
                "annual_family_income": {
                    "declared": 500000,
                    "ocr": 450000,
                    "declared_source": "APPLICANT_DECLARED",
                    "ocr_source": "OCR_PROVISIONAL",
                    "conflict": True
                }
            }
        )

        # 13. Deterministic Eligibility Pre-Evaluation
        eval_result = {}
        try:
            eval_result = RuleEvaluationService.evaluate(
                application=demo_app,
                actor=officer_user,
                record_evaluation=True
            )
        except Exception:
            pass

        return {
            "status": "SUCCESS",
            "message": "Demo scenario initialized successfully.",
            "application_id": str(demo_app.id),
            "application_number": DEMO_APPLICATION_NUMBER,
            "queue_item_id": str(queue_item.id),
            "document_id": str(doc.id),
            "applicant": {
                "username": DEMO_APPLICANT_USERNAME,
                "name": "Demo ST Applicant",
                "state": "Madhya Pradesh",
                "district": "Mandla",
                "category": "ST",
                "declared_income": 500000
            },
            "ocr_extracted": {
                "certificate_number": "TEST-2026-001",
                "income": 450000,
                "state": "MADHYA PRADESH",
                "district": "MANDLA",
                "trust_level": "OCR_PROVISIONAL"
            },
            "conflict": {
                "type": "MATERIAL_CONFLICT",
                "field": "annual_family_income",
                "declared": 500000,
                "extracted": 450000
            },
            "initial_eligibility": eval_result.get("status", "NEEDS_REVIEW")
        }
