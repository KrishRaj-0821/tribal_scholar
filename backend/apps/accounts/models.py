import uuid
from django.contrib.auth.models import AbstractUser
from django.db import models

class UserRole(models.TextChoices):
    ADMIN = 'ADMIN', 'Ministry/System Administrator'
    SCRUTINY_OFFICER = 'SCRUTINY_OFFICER', 'Scrutiny Officer'
    VERIFYING_AUTHORITY = 'VERIFYING_AUTHORITY', 'Verifying Authority'
    SANCTIONING_OFFICER = 'SANCTIONING_OFFICER', 'Sanctioning Officer'
    APPLICANT = 'APPLICANT', 'Scholarship/Fellowship Applicant'

class User(AbstractUser):
    """
    Custom user model supporting role-based access control (RBAC).
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    role = models.CharField(
        max_length=30,
        choices=UserRole.choices,
        default=UserRole.APPLICANT,
        help_text="Designated authority or applicant role."
    )
    phone_number = models.CharField(max_length=15, blank=True)
    is_verified = models.BooleanField(
        default=False,
        help_text="Designates whether this user has completed baseline identity verification."
    )

    class Meta:
        ordering = ['username']

    @property
    def is_scheme_admin(self) -> bool:
        return self.is_superuser or self.role == UserRole.ADMIN

    @property
    def is_officer(self) -> bool:
        return self.role in {
            UserRole.SCRUTINY_OFFICER,
            UserRole.VERIFYING_AUTHORITY,
            UserRole.SANCTIONING_OFFICER,
            UserRole.ADMIN
        }

    @property
    def is_applicant(self) -> bool:
        return self.role == UserRole.APPLICANT

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"
