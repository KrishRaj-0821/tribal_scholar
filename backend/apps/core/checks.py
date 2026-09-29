from django.core.checks import Error, Warning, register, Tags
from django.conf import settings

@register(Tags.compatibility)
def check_scheme_configuration_integrity(app_configs, **kwargs):
    """
    Automated startup system check verifying statutory scheme configuration.
    """
    if not getattr(settings, 'ENFORCE_STRICT_SCHEME_VALIDATION', True):
        return []

    # Import locally to avoid app registry readiness issues during early startup
    try:
        from apps.schemes.models import SchemeVersion
        from apps.core.services import validate_scheme_version_integrity
    except ImportError:
        return []

    errors = []
    try:
        for version in SchemeVersion.objects.all():
            version_errors = validate_scheme_version_integrity(version)
            for err in version_errors:
                errors.append(
                    Error(
                        err,
                        hint="Ensure all rules and reference set items link to a SourceDocument, and active versions have workflows and verified rules.",
                        obj=version,
                        id=f"tribal_scholar.E001"
                    )
                )
    except Exception:
        # Tables might not be migrated yet on initial migrate
        pass

    return errors
