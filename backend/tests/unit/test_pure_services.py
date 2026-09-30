from apps.schemes.data_quality import DataQualityValidator


class TestDataQualityValidatorPureService:
    """Pure unit tests for deterministic data quality verification."""

    def test_detects_negative_income(self):
        dossier = {
            "applicant": {"annual_family_income": -50000},
            "application": {}
        }
        issues = DataQualityValidator.validate(dossier)
        assert len(issues) == 1
        assert issues[0]["type"] == "NEGATIVE_INCOME"
        assert issues[0]["blocking"] is True

    def test_detects_malformed_income_string(self):
        dossier = {
            "applicant": {"annual_family_income": "not-a-number"},
            "application": {}
        }
        issues = DataQualityValidator.validate(dossier)
        assert any(i["type"] == "MALFORMED_INCOME" for i in issues)

    def test_detects_invalid_applicant_section_type(self):
        dossier = {
            "applicant": "invalid_string_instead_of_dict",
            "application": {}
        }
        issues = DataQualityValidator.validate(dossier)
        assert any(i["type"] == "INVALID_TYPE" and i["field"] == "applicant" for i in issues)

    def test_detects_future_dob(self):
        dossier = {
            "applicant": {"date_of_birth": "2099-01-01"},
            "application": {}
        }
        issues = DataQualityValidator.validate(dossier)
        assert any(i["type"] == "FUTURE_DATE_PROHIBITED" for i in issues)

    def test_clean_dossier_has_no_issues(self):
        dossier = {
            "applicant": {
                "annual_family_income": 450000,
                "date_of_birth": "2002-05-15",
                "community": "ST"
            },
            "application": {
                "academic_year": "2025-26",
                "course_level": "POSTGRADUATE"
            }
        }
        issues = DataQualityValidator.validate(dossier)
        assert len(issues) == 0
