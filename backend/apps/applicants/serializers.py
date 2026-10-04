from rest_framework import serializers
from apps.applicants.models import ApplicantProfile, CommunityCategory, GenderCategory


class ApplicantProfileSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    email = serializers.EmailField(source='user.email', required=False)
    first_name = serializers.CharField(source='user.first_name', required=False, allow_blank=True)
    last_name = serializers.CharField(source='user.last_name', required=False, allow_blank=True)
    phone_number = serializers.CharField(source='user.phone_number', required=False, allow_blank=True)
    completion_percentage = serializers.SerializerMethodField()

    class Meta:
        model = ApplicantProfile
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name', 'phone_number',
            'community', 'pvtg_group_name', 'caste_certificate_number',
            'caste_certificate_issuing_authority', 'annual_family_income',
            'income_certificate_number', 'date_of_birth', 'gender',
            'is_disabled', 'disability_percentage', 'udid_number',
            'completion_percentage', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_completion_percentage(self, obj) -> int:
        fields_to_check = [
            bool(obj.user.first_name),
            bool(obj.user.email),
            bool(obj.user.phone_number),
            bool(obj.community),
            bool(obj.caste_certificate_number),
            bool(obj.annual_family_income is not None),
            bool(obj.income_certificate_number),
            bool(obj.date_of_birth),
            bool(obj.gender),
        ]
        completed = sum(1 for f in fields_to_check if f)
        total = len(fields_to_check)
        return int((completed / total) * 100)

    def to_internal_value(self, data):
        data_copy = data.copy() if hasattr(data, 'copy') else dict(data)
        nested_user = data_copy.pop('user', None)
        if isinstance(nested_user, dict):
            for k, v in nested_user.items():
                if k not in data_copy and v is not None:
                    data_copy[k] = v
        return super().to_internal_value(data_copy)

    def update(self, instance, validated_data):
        user_data = validated_data.pop('user', {})
        user = instance.user

        for attr, value in user_data.items():
            setattr(user, attr, value)
        user.save()

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        return instance
