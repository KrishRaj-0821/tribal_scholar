from django.urls import path
from apps.applicants.views import ApplicantProfileView

urlpatterns = [
    path('profile/', ApplicantProfileView.as_view(), name='applicant-profile'),
    path('profile', ApplicantProfileView.as_view(), name='applicant-profile-noslash'),
]
