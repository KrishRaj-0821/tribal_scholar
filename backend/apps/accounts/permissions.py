from rest_framework import permissions

class IsSchemeAdmin(permissions.BasePermission):
    """
    Custom permission: Only authorized ADMIN roles can mutate scheme configuration.
    Read-only access is allowed for authenticated users.
    """
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return bool(request.user and request.user.is_authenticated)
        return bool(request.user and request.user.is_authenticated and request.user.is_scheme_admin)

class IsOfficerOrAdmin(permissions.BasePermission):
    """
    Permission allowing officers or administrators to view/act upon applications.
    """
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_officer)

class IsApplicantOnly(permissions.BasePermission):
    """
    Permission strictly for student applicants.
    """
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_applicant)
