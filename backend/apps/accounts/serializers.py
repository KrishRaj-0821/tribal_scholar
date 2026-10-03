from rest_framework import serializers
from apps.accounts.models import User, UserRole
from apps.applicants.models import ApplicantProfile, CommunityCategory


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'role', 'phone_number', 'is_verified', 'is_staff', 'is_superuser']


class RegisterSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    phone_number = serializers.CharField(max_length=15, required=False, allow_blank=True)
    community = serializers.ChoiceField(choices=CommunityCategory.choices, default=CommunityCategory.ST)
    annual_family_income = serializers.DecimalField(max_digits=12, decimal_places=2, default=0.00)

    def create(self, validated_data):
        community = validated_data.pop('community', 'ST')
        income = validated_data.pop('annual_family_income', 0.00)
        password = validated_data.pop('password')
        # Public registration creates APPLICANT only
        role = UserRole.APPLICANT

        user = User.objects.create_user(
            password=password,
            role=role,
            **validated_data
        )

        ApplicantProfile.objects.create(
            user=user,
            community=community,
            annual_family_income=income,
            is_synthetic=False
        )

        return user

