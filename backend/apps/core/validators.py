import re
from django.core.exceptions import ValidationError

ACADEMIC_YEAR_REGEX = re.compile(r'^20\d{2}-\d{2}$')
SHA256_REGEX = re.compile(r'^[a-fA-F0-9]{64}$')

def validate_academic_year(value):
    """Ensure academic year conforms to YYYY-YY standard (e.g. 2025-26)."""
    if not value or not ACADEMIC_YEAR_REGEX.match(value):
        raise ValidationError(
            f"Invalid academic year format '{value}'. Expected format is 'YYYY-YY' (e.g., '2025-26')."
        )

def validate_sha256_checksum(value):
    """Ensure checksum is a valid 64-character SHA-256 hexadecimal string."""
    if value and not SHA256_REGEX.match(value):
        raise ValidationError(
            f"Invalid SHA-256 checksum '{value}'. Expected 64-character hex string."
        )
