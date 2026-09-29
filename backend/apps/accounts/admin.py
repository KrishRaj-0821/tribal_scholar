from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ['username', 'email', 'role', 'is_verified', 'is_staff', 'is_active']
    list_filter = ['role', 'is_verified', 'is_staff', 'is_active']
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Tribal Scholar RBAC', {'fields': ('role', 'phone_number', 'is_verified')}),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Tribal Scholar RBAC', {'fields': ('role', 'phone_number', 'is_verified')}),
    )
