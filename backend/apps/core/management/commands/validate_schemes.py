from django.core.management.base import BaseCommand, CommandError
from apps.core.services import validate_all_schemes, SchemeConfigurationValidationError

class Command(BaseCommand):
    help = 'Validate all scheme versions, rules, workflows, and reference sets for statutory provenance.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Executing Statutory Scheme Configuration Integrity Checks..."))
        try:
            validate_all_schemes()
            self.stdout.write(self.style.SUCCESS("All SchemeVersions, SchemeRules, and ReferenceSets passed statutory integrity validation!"))
        except SchemeConfigurationValidationError as exc:
            self.stderr.write(self.style.ERROR("Validation Failed with the following errors:"))
            for err in exc.error_list:
                self.stderr.write(self.style.ERROR(f"  - {err}"))
            raise CommandError("Scheme configuration integrity validation failed.")
