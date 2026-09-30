import pytest
from django.core.exceptions import ValidationError
from apps.core.validators import validate_academic_year, validate_sha256_checksum


class TestAcademicYearValidator:
    """Pure unit tests for academic year format validation (YYYY-YY)."""

    @pytest.mark.parametrize("valid_year", [
        "2024-25",
        "2025-26",
        "2026-27",
        "2030-31",
    ])
    def test_valid_academic_years(self, valid_year):
        # Should not raise any ValidationError
        validate_academic_year(valid_year)

    @pytest.mark.parametrize("invalid_year", [
        "",
        None,
        "2025",
        "25-26",
        "2025-2026",
        "1999-00",
        "2025/26",
        "2025_26",
        "2025-260",
    ])
    def test_invalid_academic_years(self, invalid_year):
        with pytest.raises(ValidationError, match="Invalid academic year format"):
            validate_academic_year(invalid_year)


class TestSha256ChecksumValidator:
    """Pure unit tests for SHA-256 checksum format validation (64-char hex)."""

    def test_valid_sha256_checksum(self):
        valid_checksum = "a" * 64
        validate_sha256_checksum(valid_checksum)
        valid_mixed_hex = ("0123456789abcdefABCDEF" * 3)[:64]
        validate_sha256_checksum(valid_mixed_hex)

    def test_empty_or_none_allowed(self):
        # Optional field validator allows empty/None
        validate_sha256_checksum(None)
        validate_sha256_checksum("")

    @pytest.mark.parametrize("invalid_checksum", [
        "a" * 63,  # too short
        "a" * 65,  # too long
        "z" * 64,  # non-hex
        "g" + "0" * 63,
    ])
    def test_invalid_sha256_checksum(self, invalid_checksum):
        with pytest.raises(ValidationError, match="Invalid SHA-256 checksum"):
            validate_sha256_checksum(invalid_checksum)
