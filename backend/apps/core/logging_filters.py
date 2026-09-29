import re
import logging
from typing import Any

class SensitiveDataRedactingFilter(logging.Filter):
    """
    Log filter that redacts sensitive information from log messages and arguments:
    - Passwords and database credentials
    - Authentication tokens (Bearer, JWT, session, refresh)
    - API keys and secrets
    - Sensitive applicant PII (e.g. 12-digit Aadhaar numbers)
    - Document binary contents / data URLs
    """

    PATTERNS = [
        (re.compile(r'(password[\'\"]?\s*[:=]\s*[\'\"]?)[^\'\"\s,]+([\'\"]?)', re.IGNORECASE), r'\1[REDACTED]\2'),
        (re.compile(r'(secret[\'\"]?\s*[:=]\s*[\'\"]?)[^\'\"\s,]+([\'\"]?)', re.IGNORECASE), r'\1[REDACTED]\2'),
        (re.compile(r'(api_key[\'\"]?\s*[:=]\s*[\'\"]?)[^\'\"\s,]+([\'\"]?)', re.IGNORECASE), r'\1[REDACTED]\2'),
        (re.compile(r'(token[\'\"]?\s*[:=]\s*[\'\"]?)[^\'\"\s,]+([\'\"]?)', re.IGNORECASE), r'\1[REDACTED]\2'),
        (re.compile(r'(access_token[\'\"]?\s*[:=]\s*[\'\"]?)[^\'\"\s,]+([\'\"]?)', re.IGNORECASE), r'\1[REDACTED]\2'),
        (re.compile(r'(refresh_token[\'\"]?\s*[:=]\s*[\'\"]?)[^\'\"\s,]+([\'\"]?)', re.IGNORECASE), r'\1[REDACTED]\2'),
        (re.compile(r'(Bearer\s+)[A-Za-z0-9\-\._~\+\/]+=*', re.IGNORECASE), r'\1[REDACTED]'),
        (re.compile(r'(postgres(?:ql)?://[^:]+:)[^@]+(@)', re.IGNORECASE), r'\1[REDACTED]\2'),
        (re.compile(r'\b\d{4}\s?\d{4}\s?\d{4}\b'), r'[REDACTED-AADHAAR]'),
        (re.compile(r'data:[^;]+;base64,[A-Za-z0-9+/=]{20,}'), r'[REDACTED-DOCUMENT-CONTENT]'),
    ]

    def _sanitize(self, val: Any) -> Any:
        if isinstance(val, str):
            res = val
            for pattern, repl in self.PATTERNS:
                res = pattern.sub(repl, res)
            return res
        elif isinstance(val, dict):
            sanitized = {}
            for k, v in val.items():
                if any(s in k.lower() for s in ['password', 'secret', 'token', 'key', 'credential', 'aadhaar']):
                    sanitized[k] = '[REDACTED]'
                else:
                    sanitized[k] = self._sanitize(v)
            return sanitized
        elif isinstance(val, (list, tuple)):
            return [self._sanitize(item) for item in val]
        return val

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = self._sanitize(record.msg)
        if record.args:
            if isinstance(record.args, dict):
                record.args = self._sanitize(record.args)
            elif isinstance(record.args, tuple):
                record.args = tuple(self._sanitize(arg) for arg in record.args)
        return True
