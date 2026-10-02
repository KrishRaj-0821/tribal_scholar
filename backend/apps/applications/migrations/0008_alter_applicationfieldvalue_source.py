# Generated manually for FieldValueSource reconciliation
from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('applications', '0007_application_last_modified_at_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='applicationfieldvalue',
            name='source',
            field=models.CharField(
                choices=[
                    ('OFFICER_VERIFIED', 'Officer Verified'),
                    ('OFFICIAL_INTEGRATION', 'Official Integration (e.g. DigiLocker)'),
                    ('VERIFIED_DOCUMENT', 'Verified Document Extraction'),
                    ('SYSTEM', 'System Calculated'),
                    ('APPLICANT_DECLARED', 'Applicant Declared'),
                    ('OCR_PROVISIONAL', 'OCR Extraction (Provisional)')
                ],
                default='APPLICANT_DECLARED',
                help_text='Source provenance for this value',
                max_length=50
            ),
        ),
    ]
