import logging
import pytest
from apps.core.logging_filters import SensitiveDataRedactingFilter


class TestSensitiveDataRedactingFilter:
    """Pure unit tests for sensitive data log redaction filter."""

    @pytest.fixture
    def filter_instance(self):
        return SensitiveDataRedactingFilter()

    def _make_record(self, msg, args=None):
        return logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg=msg,
            args=args or (),
            exc_info=None
        )

    def test_redacts_password_in_log_message(self, filter_instance):
        record = self._make_record("User login failed for password='SecretPassword123'")
        filter_instance.filter(record)
        assert "SecretPassword123" not in record.msg
        assert "password='[REDACTED]'" in record.msg

    def test_redacts_database_connection_string(self, filter_instance):
        record = self._make_record("Connecting to postgresql://postgres:MySecretPass123@127.0.0.1:5432/db")
        filter_instance.filter(record)
        assert "MySecretPass123" not in record.msg
        assert "[REDACTED]@" in record.msg

    def test_redacts_bearer_token(self, filter_instance):
        record = self._make_record("Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.xyz123")
        filter_instance.filter(record)
        assert "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.xyz123" not in record.msg
        assert "Bearer [REDACTED]" in record.msg

    def test_redacts_aadhaar_pii(self, filter_instance):
        record = self._make_record("Applicant Aadhaar number verified: 1234 5678 9012")
        filter_instance.filter(record)
        assert "1234 5678 9012" not in record.msg
        assert "[REDACTED-AADHAAR]" in record.msg

    def test_redacts_dict_arguments(self, filter_instance):
        args = {
            "username": "scholar_01",
            "password": "SuperSecretPassword!",
            "token": "token-xyz-12345",
            "api_key": "key-abcdef-67890",
            "safe_field": "visible_value"
        }
        record = self._make_record("User audit event: %s", (args,))
        filter_instance.filter(record)
        sanitized_dict = record.args
        assert sanitized_dict["password"] == "[REDACTED]"
        assert sanitized_dict["token"] == "[REDACTED]"
        assert sanitized_dict["api_key"] == "[REDACTED]"
        assert sanitized_dict["safe_field"] == "visible_value"
