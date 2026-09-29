import re
from datetime import datetime, date
from typing import Dict, Any, List, Optional, Tuple
from django.core.exceptions import ValidationError
from apps.schemes.models import SchemeVersion
from apps.applications.models import (
    Application, ApplicationFieldDefinition, ApplicationFieldValue,
    FieldDataType, FieldValueSource, SOURCE_TRUST_RANK
)

class FieldTrustResolver:
    """
    Deterministic Field-Trust Hierarchy:
    OFFICER (50) > OFFICIAL_INTEGRATION (40) > VERIFIED_DOCUMENT (30) > SYSTEM (25) > APPLICANT (20) > OCR (10)
    
    Invariants:
    1. Lower-trust values (e.g. OCR_PROVISIONAL) NEVER overwrite higher-trust values (e.g. APPLICANT_DECLARED).
    2. VERIFIED_DOCUMENT and OFFICIAL_INTEGRATION outrank APPLICANT_DECLARED.
    3. OFFICER_VERIFIED outranks all other sources.
    4. All historical observations are preserved in ApplicationFieldValue.
    """

    @classmethod
    def get_effective_values(cls, application: Application) -> Dict[str, Dict[str, Any]]:
        """
        Returns a dictionary mapping field_code to:
        {
            "value": ...,
            "source": ...,
            "verification_status": ...,
            "confidence": ...,
            "trust_rank": ...,
            "field_definition_id": ...,
            "created_at": ...
        }
        """
        effective_map = {}
        values_qs = (
            ApplicationFieldValue.objects.filter(application=application)
            .select_related('field_definition')
            .order_by('created_at')
        )

        for val in values_qs:
            code = val.field_definition.field_code
            current = effective_map.get(code)
            val_dt = val.created_at
            # Higher trust rank wins. If same trust rank, newer timestamp wins.
            if current is None or val.trust_rank > current['trust_rank'] or (
                val.trust_rank == current['trust_rank'] and val_dt and (not current['_created_at_dt'] or val_dt >= current['_created_at_dt'])
            ):
                effective_map[code] = {
                    "value": val.value_json,
                    "source": val.source,
                    "verification_status": getattr(val, 'verification_status', 'UNVERIFIED'),
                    "confidence": val.confidence,
                    "trust_rank": val.trust_rank,
                    "field_definition_id": str(val.field_definition_id),
                    "created_at": val.created_at.isoformat() if val.created_at else None,
                    "_created_at_dt": val_dt
                }

        # Clean up temporary comparison field
        for item in effective_map.values():
            item.pop('_created_at_dt', None)

        return effective_map

    @classmethod
    def set_field_value(
        cls,
        application: Application,
        field_code: str,
        value: Any,
        source: str = FieldValueSource.APPLICANT,
        confidence: float = 1.0,
        user=None
    ) -> ApplicationFieldValue:
        """
        Appends a new value observation for a field.
        """
        field_def = ApplicationFieldDefinition.objects.filter(
            scheme_version=application.scheme_version,
            field_code=field_code
        ).first()

        if not field_def:
            raise ValidationError(
                f"Field code '{field_code}' is not defined for SchemeVersion '{application.scheme_version}'."
            )

        new_val = ApplicationFieldValue.objects.create(
            application=application,
            field_definition=field_def,
            value_json=value,
            source=source,
            confidence=confidence,
            entered_by=user
        )
        return new_val


class ApplicationFormValidator:
    """
    Authoritative server-side validation against ApplicationFieldDefinition metadata.
    Validates data types, ranges, enums, required fields, and conditional visibility.
    """

    @classmethod
    def evaluate_condition(cls, condition: Dict[str, Any], current_values: Dict[str, Any]) -> bool:
        """
        Evaluates a declarative visibility condition, e.g.:
        {"depends_on": "course_level", "operator": "==", "value": "PHD"}
        """
        if not condition:
            return True

        depends_on = condition.get("depends_on") or condition.get("field")
        operator = condition.get("operator", "==")
        expected_val = condition.get("value")

        if not depends_on:
            return True

        observed = current_values.get(depends_on)
        # Normalize comparison
        if operator in ("==", "equals", "EQUALS"):
            return str(observed).upper() == str(expected_val).upper()
        elif operator in ("!=", "not_equals", "NOT_EQUALS"):
            return str(observed).upper() != str(expected_val).upper()
        elif operator in ("in", "IN"):
            if isinstance(expected_val, list):
                return str(observed).upper() in [str(x).upper() for x in expected_val]
            return False
        return True

    @classmethod
    def validate_submission(
        cls,
        scheme_version: SchemeVersion,
        submitted_data: Dict[str, Any]
    ) -> Tuple[bool, List[Dict[str, Any]]]:
        """
        Validates all submitted field values against scheme version field definitions.
        Returns (is_valid, errors_list).
        """
        errors = []
        field_defs = ApplicationFieldDefinition.objects.filter(
            scheme_version=scheme_version,
            status='ACTIVE'
        ).order_by('display_order')

        for fdef in field_defs:
            code = fdef.field_code
            schema = fdef.validation_schema or {}
            vis_cond = schema.get("visibility_condition") or schema.get("visibility")

            # Check conditional visibility
            is_visible = True
            if vis_cond:
                is_visible = cls.evaluate_condition(vis_cond, submitted_data)

            # If hidden by condition, it is not required and not validated
            if not is_visible:
                continue

            value = submitted_data.get(code)
            is_empty = value is None or (isinstance(value, str) and value.strip() == "")

            # 1. Required Check
            if fdef.required and is_empty:
                errors.append({
                    "field": code,
                    "error_type": "REQUIRED_FIELD_MISSING",
                    "message": f"Field '{fdef.label}' is required."
                })
                continue

            if is_empty:
                continue

            # 2. Type & Format Check
            val_type = fdef.data_type

            if val_type in (FieldDataType.NUMBER, FieldDataType.CURRENCY):
                try:
                    num_val = float(value)
                    # Range check
                    if "min" in schema and num_val < schema["min"]:
                        errors.append({
                            "field": code,
                            "error_type": "VALUE_TOO_LOW",
                            "message": f"Field '{fdef.label}' must be at least {schema['min']}."
                        })
                    if "max" in schema and num_val > schema["max"]:
                        errors.append({
                            "field": code,
                            "error_type": "VALUE_TOO_HIGH",
                            "message": f"Field '{fdef.label}' cannot exceed {schema['max']}."
                        })
                except (ValueError, TypeError):
                    errors.append({
                        "field": code,
                        "error_type": "INVALID_NUMBER",
                        "message": f"Field '{fdef.label}' must be a valid numeric amount."
                    })

            elif val_type == FieldDataType.DATE:
                try:
                    parsed_date = datetime.strptime(str(value), "%Y-%m-%d").date()
                    if schema.get("no_future_date") and parsed_date > date.today():
                        errors.append({
                            "field": code,
                            "error_type": "FUTURE_DATE_PROHIBITED",
                            "message": f"Field '{fdef.label}' cannot be a future date."
                        })
                except ValueError:
                    errors.append({
                        "field": code,
                        "error_type": "INVALID_DATE_FORMAT",
                        "message": f"Field '{fdef.label}' must be a valid date formatted YYYY-MM-DD."
                    })

            elif val_type == FieldDataType.SELECT:
                options = schema.get("options", [])
                if options:
                    allowed_values = [
                        opt.get("value") if isinstance(opt, dict) else opt for opt in options
                    ]
                    if value not in allowed_values and str(value).upper() not in [str(x).upper() for x in allowed_values]:
                        errors.append({
                            "field": code,
                            "error_type": "INVALID_CHOICE",
                            "message": f"Value '{value}' is not an allowed option for '{fdef.label}'."
                        })

            elif val_type == FieldDataType.EMAIL:
                email_pattern = r'^[^@]+@[^@]+\.[^@]+$'
                if not re.match(email_pattern, str(value)):
                    errors.append({
                        "field": code,
                        "error_type": "INVALID_EMAIL",
                        "message": f"Field '{fdef.label}' must be a valid email address."
                    })

            elif val_type == FieldDataType.PHONE:
                phone_digits = re.sub(r'\D', '', str(value))
                if len(phone_digits) < 10:
                    errors.append({
                        "field": code,
                        "error_type": "INVALID_PHONE",
                        "message": f"Field '{fdef.label}' must contain a valid 10-digit mobile number."
                    })

        return len(errors) == 0, errors


class DynamicFormGenerator:
    """
    Generates the dynamic schema definition for frontend rendering:
    GET /api/v1/schemes/{scheme_version}/application-form/
    """

    @classmethod
    def generate_form(cls, scheme_version: SchemeVersion) -> Dict[str, Any]:
        fields_qs = (
            ApplicationFieldDefinition.objects.filter(
                scheme_version=scheme_version,
                status='ACTIVE',
                applicant_visible=True
            )
            .select_related('source_document')
            .order_by('section', 'display_order', 'field_code')
        )

        sections_map = {}
        for f in fields_qs:
            sec_code = f.section
            if sec_code not in sections_map:
                sections_map[sec_code] = {
                    "code": sec_code,
                    "title": sec_code.replace('_', ' ').title(),
                    "fields": []
                }

            field_dict = {
                "id": str(f.id),
                "field_code": f.field_code,
                "label": f.label,
                "description": f.description,
                "data_type": f.data_type,
                "required": f.required,
                "display_order": f.display_order,
                "validation_schema": f.validation_schema,
                "source_document": f.source_document.title if f.source_document else None,
                "source_excerpt": f.source_excerpt,
            }
            sections_map[sec_code]["fields"].append(field_dict)

        return {
            "scheme": scheme_version.scheme.code,
            "scheme_name": scheme_version.scheme.name,
            "academic_year": scheme_version.academic_year,
            "version_number": scheme_version.version_number,
            "sections": list(sections_map.values())
        }
