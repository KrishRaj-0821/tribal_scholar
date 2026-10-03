from rest_framework.authentication import SessionAuthentication, BaseAuthentication
from rest_framework import exceptions
from django.contrib.sessions.models import Session
from django.utils import timezone
from apps.accounts.models import User


class CsrfExemptSessionAuthentication(SessionAuthentication):
    """
    SessionAuthentication that exempts API requests from standard HTML CSRF enforcement,
    enabling SPA API interactions via session cookie.
    """
    def enforce_csrf(self, request):
        return  # CSRF exemption for REST API endpoints


class SessionTokenAuthentication(BaseAuthentication):
    """
    Allows SPA clients to authenticate using a session token in the Authorization header:
    Authorization: Bearer <session_key> or Authorization: Token <session_key>
    """
    def authenticate(self, request):
        auth_header = request.headers.get('Authorization') or request.META.get('HTTP_AUTHORIZATION')
        if not auth_header:
            return None

        parts = auth_header.split()
        if len(parts) != 2:
            return None

        prefix, token = parts[0].lower(), parts[1]
        if prefix not in ('bearer', 'token'):
            return None

        try:
            session = Session.objects.get(session_key=token, expire_date__gt=timezone.now())
            session_data = session.get_decoded()
            user_id = session_data.get('_auth_user_id')
            if not user_id:
                return None
            user = User.objects.get(pk=user_id)
            if not user.is_active:
                raise exceptions.AuthenticationFailed('User account is inactive or disabled.')
            return (user, None)
        except (Session.DoesNotExist, User.DoesNotExist):
            raise exceptions.AuthenticationFailed('Invalid or expired authentication session token.')
