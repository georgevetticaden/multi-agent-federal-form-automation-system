"""
FederalRunner MCP tools - Contract-First Execution.

These tools implement the schema-first pattern where Claude:
1. Lists available wizards (federalrunner_list_wizards)
2. Gets the schema for a wizard (federalrunner_get_wizard_info) ê THE CONTRACT
3. Constructs user_data dict by reading the schema
4. Executes wizard with validated data (federalrunner_execute_wizard)

NO field_mapper.py needed - Claude does the mapping naturally!
"""

from typing import Dict, Any
import json
from pathlib import Path

from .config import get_config, FederalRunnerConfig
from .models import WizardStructure
from .schema_validator import SchemaValidator
from .playwright_client import PlaywrightClient

import logging
logger = logging.getLogger(__name__)


async def federalrunner_list_wizards() -> Dict[str, Any]:
    """
    List all available wizards.

    This is the first tool Claude calls to see what wizards are available.

    Returns:
        {
            'success': True,
            'wizards': [
                {
                    'wizard_id': 'fsa-estimator',
                    'name': 'FSA Student Aid Estimator',
                    'url': 'https://studentaid.gov/aid-estimator/',
                    'total_pages': 7,
                    'discovered_at': '2025-10-17T...'
                }
            ],
            'count': 1
        }
    """
    try:
        config = get_config()

        # UPDATED PATH: wizard-structures instead of wizard-data
        wizard_dir = config.wizards_dir / "wizard-structures"

        if not wizard_dir.exists():
            logger.error(f"L Wizards directory not found: {wizard_dir}")
            return {
                'success': False,
                'error': f'Wizards directory not found: {wizard_dir}',
                'hint': 'Make sure FederalScout has discovered at least one wizard'
            }

        # Load all wizard JSON files
        wizards = []
        for json_file in wizard_dir.glob("*.json"):
            try:
                wizard = WizardStructure.from_json_file(json_file)
                wizards.append({
                    'wizard_id': wizard.wizard_id,
                    'name': wizard.name,
                    'url': wizard.url,
                    'total_pages': wizard.total_pages,
                    'discovered_at': wizard.discovered_at.isoformat()
                })
            except Exception as e:
                logger.warning(f"Failed to load wizard from {json_file}: {e}")
                # Continue loading other wizards

        logger.info(f" Found {len(wizards)} wizard(s)")

        return {
            'success': True,
            'wizards': wizards,
            'count': len(wizards)
        }

    except Exception as e:
        logger.error(f"L Failed to list wizards: {e}")
        return {
            'success': False,
            'error': str(e),
            'error_type': type(e).__name__
        }


async def federalrunner_get_wizard_info(wizard_id: str) -> Dict[str, Any]:
    """
    Get wizard information including User Data Schema.

    P THIS RETURNS THE SCHEMA - Claude reads it to know what data to collect!

    This is the CONTRACT between Claude and FederalRunner.
    Claude reads this schema and constructs user_data dict accordingly.

    Args:
        wizard_id: Wizard identifier (e.g., "fsa-estimator")

    Returns:
        {
            'success': True,
            'wizard_id': 'fsa-estimator',
            'name': 'FSA Student Aid Estimator',
            'url': 'https://...',
            'total_pages': 7,
            'schema': {
                '$schema': 'http://json-schema.org/draft-07/schema#',
                'type': 'object',
                'required': ['birth_month', 'birth_day', ...],
                'properties': {
                    'birth_month': {
                        'type': 'string',
                        'pattern': '^(0[1-9]|1[0-2])$',
                        'description': 'Student\'s birth month (2 digits: 01-12)'
                    },
                    ...
                },
                '_claude_hints': {...},  ê Helper hints for Claude
                '_example_user_data': {...}  ê Example structure
            }
        }
    """
    try:
        config = get_config()
        validator = SchemaValidator(config)

        # 1. Load wizard structure (for metadata)
        # UPDATED PATH: wizard-structures
        wizard_path = config.wizards_dir / "wizard-structures" / f"{wizard_id}.json"

        if not wizard_path.exists():
            logger.error(f"L Wizard not found: {wizard_id}")
            return {
                'success': False,
                'error': f'Wizard not found: {wizard_id}',
                'hint': 'Call federalrunner_list_wizards() to see available wizards'
            }

        wizard = WizardStructure.from_json_file(wizard_path)

        # 2. Load User Data Schema (THE CONTRACT)
        try:
            schema = validator.load_schema(wizard_id)
        except FileNotFoundError:
            logger.error(f"L Schema not found for wizard: {wizard_id}")
            return {
                'success': False,
                'error': f'Schema not found for wizard: {wizard_id}',
                'hint': 'FederalScout needs to generate the schema for this wizard'
            }

        # 3. Enhance schema with Claude-friendly hints
        enhanced_schema = validator.enhance_schema_for_claude(schema)

        logger.info(f" Wizard info retrieved: {wizard_id}")

        # 4. Return schema + basic wizard info
        return {
            'success': True,
            'wizard_id': wizard.wizard_id,
            'name': wizard.name,
            'url': wizard.url,
            'total_pages': wizard.total_pages,
            'schema': enhanced_schema  # ê Claude reads THIS to collect user data
        }

    except Exception as e:
        logger.error(f"L Failed to get wizard info: {e}")
        return {
            'success': False,
            'error': str(e),
            'error_type': type(e).__name__
        }


async def federalrunner_execute_wizard(
    wizard_id: str,
    user_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Execute wizard with validated user data.

    This is where the Contract-First pattern comes together:
    1. Load User Data Schema
    2. Validate user_data against schema (catch errors before execution)
    3. Load Wizard Structure
    4. P Map user_data (field_id) í field_values (selector) ê THE CRITICAL MAPPING
    5. Execute atomically with Playwright

    Args:
        wizard_id: Wizard identifier (e.g., "fsa-estimator")
        user_data: Dict where keys are field_ids from schema
                   e.g., {"birth_month": "05", "parent_income": 85000}
                   Claude constructs this by reading the schema!

    Returns:
        {
            'success': True,
            'wizard_id': 'fsa-estimator',
            'results': {...extracted results...},
            'screenshots': [base64...],
            'pages_completed': 7,
            'execution_time_ms': 8500
        }

        OR if validation fails:
        {
            'success': False,
            'error': 'User data validation failed',
            'validation_errors': {
                'missing_fields': [...],
                'invalid_fields': [...]
            }
        }
    """
    try:
        config = get_config()
        validator = SchemaValidator(config)

        logger.info(f"=Ä Executing wizard: {wizard_id}")
        logger.debug(f"User data fields: {list(user_data.keys())}")

        # 1. Load User Data Schema
        try:
            schema = validator.load_schema(wizard_id)
        except FileNotFoundError as e:
            return {
                'success': False,
                'error': f'Schema not found for wizard: {wizard_id}',
                'hint': 'Call federalrunner_get_wizard_info() first'
            }

        # 2. Validate user_data against schema
        validation_result = validator.validate_user_data(user_data, schema)

        if not validation_result['valid']:
            logger.error(f"L User data validation failed")
            return {
                'success': False,
                'error': 'User data validation failed',
                'validation_errors': validation_result,
                'hint': 'Review the schema from federalrunner_get_wizard_info() and fix the user_data'
            }

        logger.info(" User data validation passed")

        # 3. Load wizard structure
        # UPDATED PATH: wizard-structures
        wizard_path = config.wizards_dir / "wizard-structures" / f"{wizard_id}.json"

        if not wizard_path.exists():
            return {
                'success': False,
                'error': f'Wizard structure not found: {wizard_id}'
            }

        wizard = WizardStructure.from_json_file(wizard_path)

        # 4. P MAP user_data (field_id) í field_values (selector)
        # This is THE CRITICAL STEP from REQ-CONTRACT-006
        field_values = {}  # selector í value

        for page in wizard.pages:
            for field in page.fields:
                field_id = field.field_id

                # Look up value by field_id in user_data
                if field_id in user_data:
                    # Map: field_id í selector
                    field_values[field.selector] = user_data[field_id]
                    logger.debug(f"  Mapped: {field_id} í {field.selector} = {user_data[field_id]}")

        logger.info(f" Mapped {len(field_values)} fields (field_id í selector)")

        # 5. Execute atomically with Playwright
        client = PlaywrightClient(config)
        result = await client.execute_wizard_atomically(wizard, field_values)

        return result

    except Exception as e:
        logger.error(f"L Execution failed: {e}")
        return {
            'success': False,
            'error': str(e),
            'error_type': type(e).__name__,
            'hint': 'Check logs for details'
        }
