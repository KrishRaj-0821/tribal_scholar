"""
Central Notification Message Templates for Ministry of Tribal Affairs (MoTA) Portal.
Strict rules:
- No sensitive information (caste details, complete financial numbers, document contents, internal audit tags).
- Clear, concise government messaging.
"""

from typing import Dict, Any

TEMPLATES = {
    "APPLICATION_SUBMITTED": (
        "Your Tribal Scholar application {application_id} has been submitted successfully. Login to view status."
    ),
    "VERIFICATION_COMPLETED": (
        "Your Tribal Scholar application {application_id} has been reviewed. Login to view the updated status."
    ),
    "NEEDS_MORE_EVIDENCE": (
        "Action required for Tribal Scholar application {application_id}. Please login to provide the requested evidence."
    ),
    "APPLICATION_STATUS_CHANGED": (
        "Your Tribal Scholar application {application_id} status has been updated to {status}. Login to view details."
    ),
    "DOCUMENT_PROCESSING_COMPLETED": (
        "Document verification completed for your Tribal Scholar application {application_id}. Login to view results."
    ),
    "OTP": (
        "Your Tribal Scholar verification OTP is {otp}. It expires in {expiry_minutes} minutes."
    ),
}


class NotificationTemplate:
    APPLICATION_SUBMITTED = "APPLICATION_SUBMITTED"
    VERIFICATION_COMPLETED = "VERIFICATION_COMPLETED"
    NEEDS_MORE_EVIDENCE = "NEEDS_MORE_EVIDENCE"
    APPLICATION_STATUS_CHANGED = "APPLICATION_STATUS_CHANGED"
    DOCUMENT_PROCESSING_COMPLETED = "DOCUMENT_PROCESSING_COMPLETED"
    OTP = "OTP"


def render_template(template_name: str, context: Dict[str, Any] = None, **kwargs) -> str:
    """
    Renders a statutory message template by substituting parameters safely.
    Accepts context dictionary or keyword arguments.
    Raises KeyError if required context variables are missing.
    """
    if template_name not in TEMPLATES:
        raise ValueError(f"Unknown notification template: '{template_name}'. Available: {list(TEMPLATES.keys())}")
    
    merged_context = {}
    if context:
        merged_context.update(context)
    if kwargs:
        merged_context.update(kwargs)

    template_str = TEMPLATES[template_name]
    return template_str.format(**merged_context)

