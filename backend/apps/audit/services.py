import threading
from typing import Optional, Any
from .models import AuditLog, AuditAction

_thread_locals = threading.local()

def set_current_request(request):
    _thread_locals.request = request

def get_current_request():
    return getattr(_thread_locals, 'request', None)

def get_client_ip(request) -> Optional[str]:
    if not request:
        return None
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')

def log_audit_event(
    entity_type: str,
    entity_id: str,
    action: str,
    actor: Optional[Any] = None,
    actor_role: str = '',
    before_json: Optional[dict] = None,
    after_json: Optional[dict] = None,
    reason: str = '',
    ip_address: Optional[str] = None
) -> AuditLog:
    """
    Append an immutable event to the statutory AuditLog.
    Automatically enriches actor and IP context from current request if available.
    """
    request = get_current_request()
    if request:
        if not actor and getattr(request, 'user', None) and request.user.is_authenticated:
            actor = request.user
            actor_role = getattr(request.user, 'role', '')
        if not ip_address:
            ip_address = get_client_ip(request)

    if actor and not actor_role:
        actor_role = getattr(actor, 'role', '')

    return AuditLog.objects.create(
        actor=actor,
        actor_role=actor_role or 'SYSTEM',
        entity_type=entity_type,
        entity_id=str(entity_id),
        action=action,
        before_json=before_json,
        after_json=after_json,
        reason=reason,
        ip_address=ip_address
    )
