import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Dict, Any, List, Optional


class DataQualityValidator:
    """
    Data Quality Layer.
    Detects dossier anomalies, missing fields, type errors, impossible dates,
    negative income, and academic year mismatches BEFORE rule evaluation.
    
    Guarantees:
    Data quality issues NEVER convert directly into arbitrary eligibility rejections (INELIGIBLE).
    Instead, un-evaluatable or malformed inputs transition to NEEDS_REVIEW.
    """

    @classmethod
    def validate(cls, dossier: Dict[str, Any], scheme_version=None) -> List[Dict[str, Any]]:
        issues: List[Dict[str, Any]] = []

        applicant = dossier.get('applicant', {})
        application = dossier.get('application', {})

        if not isinstance(applicant, dict):
            issues.append({
                "type": "INVALID_TYPE",
                "field": "applicant",
                "message": "Dossier 'applicant' section must be a dictionary object.",
                "blocking": True
            })
            applicant = {}

        if not isinstance(application, dict):
            issues.append({
                "type": "INVALID_TYPE",
                "field": "application",
                "message": "Dossier 'application' section must be a dictionary object.",
                "blocking": True
            })
            application = {}

        # 1. Negative & Malformed Income
        income_val = applicant.get('annual_family_income')
        if income_val is not None:
            try:
                dec_inc = Decimal(str(income_val))
                if dec_inc < 0:
                    issues.append({
                        "type": "NEGATIVE_INCOME",
                        "field": "applicant.annual_family_income",
                        "message": f"Annual family income cannot be negative ({dec_inc}).",
                        "blocking": True
                    })
            except (InvalidOperation, TypeError, ValueError):
                issues.append({
                    "type": "MALFORMED_INCOME",
                    "field": "applicant.annual_family_income",
                    "message": f"Annual family income '{income_val}' is malformed and cannot be parsed as a decimal currency amount.",
                    "blocking": True
                })

        # 2. Date of Birth & Future Dates
        dob_val = applicant.get('date_of_birth')
        if dob_val is not None:
            parsed_dob = None
            if isinstance(dob_val, (date, datetime)):
                parsed_dob = dob_val.date() if isinstance(dob_val, datetime) else dob_val
            elif isinstance(dob_val, str):
                for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
                    try:
                        parsed_dob = datetime.strptime(dob_val, fmt).date()
                        break
                    except ValueError:
                        continue
                if parsed_dob is None:
                    issues.append({
                        "type": "IMPOSSIBLE_DATE",
                        "field": "applicant.date_of_birth",
                        "message": f"Date of birth '{dob_val}' cannot be parsed into a valid date.",
                        "blocking": True
                    })

            if parsed_dob:
                today = date.today()
                if parsed_dob > today:
                    issues.append({
                        "type": "FUTURE_DATE_PROHIBITED",
                        "field": "applicant.date_of_birth",
                        "message": f"Date of birth '{parsed_dob}' is in the future.",
                        "blocking": True
                    })
                elif parsed_dob.year < 1900:
                    issues.append({
                        "type": "IMPOSSIBLE_DATE",
                        "field": "applicant.date_of_birth",
                        "message": f"Date of birth year '{parsed_dob.year}' is impossible.",
                        "blocking": True
                    })

        # 3. Age on July 1 checks
        age_val = applicant.get('age_on_july_1')
        if age_val is not None:
            try:
                age_int = int(age_val)
                if age_int < 0 or age_int > 120:
                    issues.append({
                        "type": "IMPOSSIBLE_DATE",
                        "field": "applicant.age_on_july_1",
                        "message": f"Age on July 1 '{age_val}' is outside plausible human lifespan (0 - 120).",
                        "blocking": True
                    })
            except (ValueError, TypeError):
                issues.append({
                    "type": "INVALID_TYPE",
                    "field": "applicant.age_on_july_1",
                    "message": f"Age on July 1 '{age_val}' must be an integer.",
                    "blocking": True
                })

        # 4. Inconsistent Academic Year
        app_ay = application.get('academic_year')
        if app_ay and scheme_version:
            if str(app_ay).strip() != str(scheme_version.academic_year).strip():
                issues.append({
                    "type": "INCONSISTENT_ACADEMIC_YEAR",
                    "field": "application.academic_year",
                    "message": f"Application academic year '{app_ay}' conflicts with target SchemeVersion '{scheme_version.academic_year}'.",
                    "blocking": True
                })

        # 5. Missing Institution Identifier when required
        if scheme_version and scheme_version.scheme.code in ("TOP_CLASS", "NFST"):
            inst_code = application.get('institute_code')
            if not inst_code or str(inst_code).strip() == "":
                issues.append({
                    "type": "MISSING_INSTITUTION_IDENTIFIER",
                    "field": "application.institute_code",
                    "message": f"Institution identifier is required for {scheme_version.scheme.code} evaluation but is missing or empty.",
                    "blocking": True
                })

        # 6. Invalid Course Level
        if 'course_level' in application:
            c_lvl = application.get('course_level')
            if c_lvl is None or (isinstance(c_lvl, str) and str(c_lvl).strip() == ""):
                issues.append({
                    "type": "INVALID_COURSE_LEVEL",
                    "field": "application.course_level",
                    "message": "Course level is blank or empty.",
                    "blocking": True
                })

        # 7. Duplicate Applicant Identifier (e.g. conflicting Aadhaar or student IDs)
        student_id_1 = applicant.get('student_id')
        student_id_2 = applicant.get('duplicate_check_id')
        if student_id_1 and student_id_2 and student_id_1 != student_id_2:
            issues.append({
                "type": "DUPLICATE_APPLICANT_IDENTIFIER",
                "field": "applicant.student_id",
                "message": "Candidate identifier mismatch detected between demographic profile and application dossier.",
                "blocking": True
            })

        return issues
