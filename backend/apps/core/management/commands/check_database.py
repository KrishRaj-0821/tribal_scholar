import sys
from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = "Verify PostgreSQL connection and integrity test database readiness."

    def handle(self, *args, **options):
        vendor = connection.vendor
        settings_dict = connection.settings_dict
        db_name = settings_dict.get("NAME", "")
        db_host = settings_dict.get("HOST", "127.0.0.1")
        db_port = settings_dict.get("PORT", "5432")

        if vendor != "postgresql":
            self.stderr.write(f"Database backend: {vendor}")
            self.stderr.write("ERROR: PostgreSQL is required for the integrity test suite.")
            sys.exit(1)

        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT version();")
                row = cursor.fetchone()
                raw_version = row[0] if row else "Unknown"
                version_str = raw_version.split(",")[0]
        except Exception as e:
            self.stderr.write(f"ERROR: Could not establish PostgreSQL connection: {e}")
            sys.exit(1)

        self.stdout.write("Database backend: PostgreSQL")
        self.stdout.write(f"Version: {version_str}")
        self.stdout.write(f"Database: {db_name}")
        self.stdout.write(f"Host: {db_host}")
        self.stdout.write(f"Port: {db_port}")
        sys.exit(0)
