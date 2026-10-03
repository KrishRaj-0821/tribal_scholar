import logging
from django.contrib.auth import authenticate, login, logout
from django.db.models import Q
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework import status

from apps.accounts.models import User, UserRole
from apps.accounts.serializers import UserSerializer, RegisterSerializer

logger = logging.getLogger('apps.accounts')


class RegisterView(APIView):
    """
    Applicant registration endpoint.
    Public registration creates APPLICANT role exclusively.
    """
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        username = serializer.validated_data['username']
        email = serializer.validated_data['email']
        if User.objects.filter(username=username).exists():
            return Response({"error": "Username already exists"}, status=status.HTTP_400_BAD_REQUEST)
        if User.objects.filter(email=email).exists():
            return Response({"error": "Email is already registered"}, status=status.HTTP_400_BAD_REQUEST)

        user = serializer.save()
        login(request, user)
        if not request.session.session_key:
            request.session.save()

        return Response({
            "message": "User registered successfully",
            "token": request.session.session_key,
            "user": UserSerializer(user).data
        }, status=status.HTTP_201_CREATED)


class LoginView(APIView):
    """
    Authoritative authentication endpoint.
    Accepts username, email, or mobile phone number along with password.
    Returns authenticated user profile, assigned role, and session token.
    """
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        identifier = request.data.get('identifier') or request.data.get('username') or request.data.get('email')
        password = request.data.get('password')
        if not identifier or not password:
            return Response({"error": "Identifier (username/email/phone) and password required"}, status=status.HTTP_400_BAD_REQUEST)

        # 1. Attempt standard Django authenticate by username
        user = authenticate(request, username=identifier, password=password)

        # 2. If not found, look up by email or phone
        if not user:
            candidate = User.objects.filter(
                Q(email__iexact=identifier) |
                Q(username__iexact=identifier) |
                Q(phone_number__iexact=identifier)
            ).first()

            if candidate and candidate.check_password(password):
                user = candidate

        if not user:
            return Response({"error": "Invalid username, email, or password"}, status=status.HTTP_401_UNAUTHORIZED)

        if not user.is_active:
            return Response({"error": "Account is disabled. Contact portal support."}, status=status.HTTP_403_FORBIDDEN)

        login(request, user)
        if not request.session.session_key:
            request.session.save()

        return Response({
            "message": "Logged in successfully",
            "token": request.session.session_key,
            "user": UserSerializer(user).data
        }, status=status.HTTP_200_OK)


class LogoutView(APIView):
    """
    Session logout endpoint: destroys session and clears authenticated state.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            request.session.flush()
        except Exception:
            pass
        logout(request)
        return Response({"message": "Logged out successfully"}, status=status.HTTP_200_OK)


class MeView(APIView):
    """
    Returns current authenticated user details and assigned sovereign role.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({
            "user": UserSerializer(request.user).data,
            "token": request.session.session_key or ""
        }, status=status.HTTP_200_OK)


class RequestOTPView(APIView):
    """
    POST /api/v1/auth/request-otp/
    Dispatches a 6-digit cryptographic OTP via Fast2SMS to the requested Indian mobile number.
    Rate-limited to 1 request per 60 seconds per phone number.
    """
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        mobile = request.data.get('mobile') or request.data.get('phone_number')
        if not mobile:
            return Response(
                {"error": "Mobile phone number is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        from apps.notifications.services import OTPService
        success, msg, masked_phone = OTPService.generate_and_send_otp(str(mobile))
        if not success:
            is_rate_limit = "wait" in msg.lower() or "recently" in msg.lower()
            return Response(
                {"error": msg, "mobile_masked": masked_phone},
                status=status.HTTP_429_TOO_MANY_REQUESTS if is_rate_limit else status.HTTP_400_BAD_REQUEST
            )

        return Response({
            "message": msg,
            "mobile_masked": masked_phone
        }, status=status.HTTP_200_OK)


class VerifyOTPView(APIView):
    """
    POST /api/v1/auth/verify-otp/
    Validates the entered 6-digit OTP against the stored cryptographic hash.
    Authenticates the applicant and returns a session token.
    """
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        mobile = request.data.get('mobile') or request.data.get('phone_number')
        otp = request.data.get('otp')
        if not mobile or not otp:
            return Response(
                {"error": "Both mobile number and OTP code are required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        import secrets
        from apps.notifications.services import OTPService
        from apps.notifications.providers.fast2sms import normalize_phone_number

        try:
            norm_phone = normalize_phone_number(str(mobile))
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        is_valid, msg, user = OTPService.verify_otp(norm_phone, str(otp))
        if not is_valid:
            return Response({"error": msg}, status=status.HTTP_400_BAD_REQUEST)

        # If user does not exist yet, provision an APPLICANT user with demographic profile
        if not user:
            from apps.applicants.models import ApplicantProfile, CommunityCategory
            username = f"st_{norm_phone[-4:]}_{secrets.token_hex(3)}"
            user = User.objects.create_user(
                username=username,
                email=f"{username}@tribal.nic.in",
                role=UserRole.APPLICANT,
                phone_number=norm_phone
            )
            ApplicantProfile.objects.create(
                user=user,
                community=CommunityCategory.ST
            )

        login(request, user)
        if not request.session.session_key:
            request.session.save()

        return Response({
            "message": "OTP verified successfully. Authenticated as applicant.",
            "token": request.session.session_key,
            "user": UserSerializer(user).data
        }, status=status.HTTP_200_OK)

