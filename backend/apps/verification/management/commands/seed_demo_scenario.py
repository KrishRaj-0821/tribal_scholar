from django.core.management.base import BaseCommand
from apps.verification.demo_service import DemoScenarioService

class Command(BaseCommand):
    help = 'Seed or reset the deterministic SIH demo scenario (APP-2026-001DB3, Material Conflict, High Priority Queue Item).'

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Initializing SIH 2026 synthetic demonstration scenario..."))
        result = DemoScenarioService.reset_demo_scenario()
        self.stdout.write(self.style.SUCCESS(
            f"Successfully seeded demo scenario!\n"
            f"Application ID: {result['application_id']} ({result['application_number']})\n"
            f"Queue Item ID: {result['queue_item_id']}\n"
            f"Document ID: {result['document_id']}\n"
            f"Conflict: {result['conflict']['type']} (Declared INR 5,00,000 vs Extracted INR 4,50,000)\n"
            f"Initial Eligibility: {result['initial_eligibility']}"
        ))
