"""
Schema-first validation for user data.

This module REPLACES traditional field_mapper.py approaches.

The User Data Schema IS the contract:
- FederalScout generates it (vision → schema)
- Claude reads it (schema → data collection)
- FederalRunner validates it (schema → validation)

NO field mapping code is needed here - Claude does the mapping naturally
by reading the schema and collecting data in the correct format.
"""

from pathlib import Path
from typing import Dict, Any, List
import json
from jsonschema import validate, ValidationError, Draft7Validator

from config import FederalRunnerConfig

import logging
logger = logging.getLogger(__name__)


class SchemaValidator:
    """
    Validates user data against User Data Schema.

    This REPLACES field_mapper.py:
    - Claude reads the schema (from federalrunner_get_wizard_info())
    - Claude collects data naturally (no hardcoded mapping)
    - This class validates the data Claude collected
    - field_id in schema matches field_id in wizard structure
    - Execution tools map field_id → selector
    """

    def __init__(self, config: FederalRunnerConfig):
        """
        Initialize schema validator with configuration.

        Args:
            config: FederalRunnerConfig with paths to schema directories
        """
        self.config = config

    def load_schema(self, wizard_id: str) -> Dict[str, Any]:
        """
        Load User Data Schema for a wizard.

        Args:
            wizard_id: Wizard identifier (e.g., "fsa-estimator")

        Returns:
            JSON Schema (draft-07) as dict

        Raises:
            FileNotFoundError: If schema file doesn't exist
            json.JSONDecodeError: If schema file is invalid JSON
        """
        # UPDATED PATH: data-schemas instead of wizard-schemas
        schema_path = self.config.wizards_dir / "data-schemas" / f"{wizard_id}-schema.json"

        if not schema_path.exists():
            logger.error(f"❌ Schema not found: {schema_path}")
            raise FileNotFoundError(
                f"Schema not found for wizard '{wizard_id}'. "
                f"Expected at: {schema_path}. "
                f"Make sure FederalScout has generated the schema for this wizard."
            )

        try:
            with open(schema_path, 'r') as f:
                schema = json.load(f)

            logger.info(f"✅ Schema loaded: {schema_path}")
            return schema

        except json.JSONDecodeError as e:
            logger.error(f"❌ Invalid JSON in schema file: {e}")
            raise

    def validate_user_data(
        self,
        user_data: Dict[str, Any],
        schema: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validate user data against User Data Schema.

        This is where we ensure Claude collected the data correctly.

        Args:
            user_data: Data collected by Claude (field_id → value)
                      e.g., {"birth_month": "05", "parent_income": 85000}
            schema: User Data Schema (from load_schema)

        Returns:
            {
                'valid': True/False,
                'errors': [...] if invalid,
                'missing_fields': [field_ids],
                'invalid_fields': [{field, value, reason}]
            }
        """
        try:
            # Validate against JSON Schema (draft-07)
            validate(user_data, schema)

            logger.info("✅ User data validation passed")

            return {
                'valid': True,
                'message': 'User data conforms to schema'
            }

        except ValidationError as e:
            logger.error(f"❌ User data validation failed: {e.message}")

            # Extract helpful error information for Claude
            missing_fields = self._extract_missing_fields(e, schema, user_data)
            invalid_fields = self._extract_invalid_fields(e, schema)

            return {
                'valid': False,
                'error': e.message,
                'error_path': list(e.path),
                'missing_fields': missing_fields,
                'invalid_fields': invalid_fields,
                'hint': 'Call federalrunner_get_wizard_info() to review the schema requirements'
            }

    def _extract_missing_fields(
        self,
        error: ValidationError,
        schema: Dict[str, Any],
        user_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Extract which required fields are missing.

        Returns detailed info to help Claude understand what's needed.

        Args:
            error: ValidationError from jsonschema
            schema: User Data Schema
            user_data: User data that was validated

        Returns:
            List of dicts with field details:
            [
                {
                    'field_id': 'birth_month',
                    'description': 'Student\'s birth month (2 digits: 01-12)',
                    'type': 'string',
                    'pattern': '^(0[1-9]|1[0-2])$'
                }
            ]
        """
        missing = []

        # Check if this is a required field error
        if 'required' in error.message.lower() or error.validator == 'required':
            required_fields = schema.get('required', [])
            provided_fields = set(user_data.keys())

            # Find which required fields are missing
            for field_id in required_fields:
                if field_id not in provided_fields:
                    field_schema = schema.get('properties', {}).get(field_id, {})

                    missing.append({
                        'field_id': field_id,
                        'description': field_schema.get('description', 'No description'),
                        'type': field_schema.get('type'),
                        'pattern': field_schema.get('pattern'),
                        'enum': field_schema.get('enum'),
                        'examples': field_schema.get('examples')
                    })

        return missing

    def _extract_invalid_fields(
        self,
        error: ValidationError,
        schema: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Extract which fields have invalid values.

        Returns detailed info about what's wrong and how to fix it.

        Args:
            error: ValidationError from jsonschema
            schema: User Data Schema

        Returns:
            List of dicts with field validation errors:
            [
                {
                    'field_id': 'birth_month',
                    'provided_value': '5',
                    'expected_type': 'string',
                    'expected_pattern': '^(0[1-9]|1[0-2])$',
                    'reason': 'Value must match pattern (use zero-padded month: 01-12)'
                }
            ]
        """
        invalid = []

        # Get field path from error
        field_path = list(error.path)
        field_id = field_path[0] if field_path else None

        if not field_id:
            # Can't extract field-specific info
            return []

        field_schema = schema.get('properties', {}).get(field_id, {})

        # Build error detail
        error_detail = {
            'field_id': field_id,
            'provided_value': error.instance,
            'expected_type': field_schema.get('type'),
            'description': field_schema.get('description', 'No description')
        }

        # Add specific validation details based on error type
        if error.validator == 'pattern':
            error_detail['expected_pattern'] = field_schema.get('pattern')
            error_detail['reason'] = (
                f"Value must match pattern: {field_schema.get('pattern')}. "
                f"See description: {field_schema.get('description')}"
            )

        elif error.validator == 'enum':
            error_detail['allowed_values'] = field_schema.get('enum')
            error_detail['reason'] = (
                f"Value must be one of: {field_schema.get('enum')}"
            )

        elif error.validator == 'type':
            error_detail['reason'] = (
                f"Value must be of type: {field_schema.get('type')}. "
                f"Provided: {type(error.instance).__name__}"
            )

        elif error.validator == 'minimum':
            error_detail['minimum'] = field_schema.get('minimum')
            error_detail['reason'] = (
                f"Value must be >= {field_schema.get('minimum')}"
            )

        elif error.validator == 'maximum':
            error_detail['maximum'] = field_schema.get('maximum')
            error_detail['reason'] = (
                f"Value must be <= {field_schema.get('maximum')}"
            )

        else:
            error_detail['reason'] = error.message

        invalid.append(error_detail)

        return invalid

    def enhance_schema_for_claude(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enhance schema with Claude-friendly hints and examples.

        This makes it easier for Claude to understand how to collect and format data.

        Args:
            schema: Raw User Data Schema

        Returns:
            Enhanced schema with additional metadata
        """
        enhanced_schema = {
            **schema,
            '_claude_hints': {
                'workflow': [
                    '1. Read the "required" array to see which fields are mandatory',
                    '2. Read each field in "properties" to understand type and validation',
                    '3. Extract data from user\'s natural language message',
                    '4. Transform to match schema types and patterns',
                    '5. Call federalrunner_execute_wizard() with the constructed dict'
                ],
                'common_transforms': {
                    'dates': {
                        'pattern': 'Convert month names to zero-padded numbers',
                        'examples': ['May → "05"', 'January → "01"', 'December → "12"']
                    },
                    'currency': {
                        'pattern': 'Remove $ and commas, convert k/m to numbers',
                        'examples': ['$120k → 120000', '$1.5M → 1500000', '$85,000 → 85000']
                    },
                    'states': {
                        'pattern': 'Use full state name (check enum for exact match)',
                        'examples': ['IL → Illinois', 'CA → California']
                    },
                    'boolean_synonyms': {
                        'pattern': 'Convert natural language to enum values',
                        'examples': [
                            'single/unmarried → "unmarried"',
                            'married/remarried → "married"',
                            'yes/yep/yeah → "yes"',
                            'no/nope → "no"'
                        ]
                    }
                }
            }
        }

        # Add example user_data structure
        example_data = {}
        for field_id, field_schema in schema.get('properties', {}).items():
            examples = field_schema.get('examples')
            if examples and len(examples) > 0:
                example_data[field_id] = examples[0]
            else:
                # Generate example based on type
                field_type = field_schema.get('type')
                if field_type == 'string':
                    example_data[field_id] = field_schema.get('pattern', 'example_value')
                elif field_type == 'integer' or field_type == 'number':
                    example_data[field_id] = field_schema.get('minimum', 0)
                elif field_type == 'boolean':
                    example_data[field_id] = True

        enhanced_schema['_example_user_data'] = example_data

        return enhanced_schema
