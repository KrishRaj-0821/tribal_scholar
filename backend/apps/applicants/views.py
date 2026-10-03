from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from django.shortcuts import get_object_or_404

from apps.applicants.models import ApplicantProfile, CommunityCategory
from apps.applicants.serializers import ApplicantProfileSerializer


class ApplicantProfileView(APIView):
    """
    GET /api/v1/applicants/profile/
    PATCH /api/v1/applicants/profile/
    Returns and updates the profile of the currently authenticated applicant.
    """
    permission_classes = [IsAuthenticated]

    def get_or_create_profile(self, user):
        profile = getattr(user, 'applicant_profile', None)
        if not profile:
            profile, _ = ApplicantProfile.objects.get_or_create(
                user=user,
                defaults={
                    "community": CommunityCategory.ST,
                    "annual_family_income": 0.00,
                    "is_synthetic": False
                }
            )
        return profile

    def get(self, request):
        profile = self.get_or_create_profile(request.user)
        serializer = ApplicantProfileSerializer(profile)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request):
        profile = self.get_or_create_profile(request.user)
        serializer = ApplicantProfileSerializer(profile, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
