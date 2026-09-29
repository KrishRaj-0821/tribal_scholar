import uuid
from django.db import models
from django.conf import settings

class CommunityCategory(models.TextChoices):
    ST = 'ST', 'Scheduled Tribe'
    PVTG = 'PVTG', 'Particularly Vulnerable Tribal Group'
    OTHER = 'OTHER', 'Other (Non-ST)'

class GenderCategory(models.TextChoices):
    FEMALE = 'FEMALE', 'Female'
    MALE = 'MALE', 'Male'
    OTHER = 'OTHER', 'Other / Transgender'

class ApplicantProfile(models.Model):
    """
    Applicant demographic profile. Supports synthetic applicant generation
    for testing and strict protection of sensitive PII.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='applicant_profile'
    )
    community = models.CharField(
        max_length=20,
        choices=CommunityCategory.choices,
        default=CommunityCategory.ST
    )
    pvtg_group_name = models.CharField(max_length=150, blank=True, help_text="Specific PVTG group if applicable")
    caste_certificate_number = models.CharField(max_length=100, blank=True)
    caste_certificate_issuing_authority = models.CharField(max_length=150, blank=True)
    annual_family_income = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        help_text="Gross annual parental/family income in INR"
    )
    income_certificate_number = models.CharField(max_length=100, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=20, choices=GenderCategory.choices, default=GenderCategory.FEMALE)
    is_disabled = models.BooleanField(default=False)
    disability_percentage = models.PositiveIntegerField(default=0)
    udid_number = models.CharField(max_length=100, blank=True)
    is_synthetic = models.BooleanField(
        default=True,
        help_text="Flag indicating synthetic / mock applicant for development and testing"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['user__username']

    def __str__(self):
        return f"{self.user.username} - {self.community} ({'Synthetic' if self.is_synthetic else 'Real'})"
