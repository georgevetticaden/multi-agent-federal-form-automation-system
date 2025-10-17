"""
Local execution tests for FederalRunner MCP Tools.

Tests the three MCP tools that will be exposed via HTTP endpoint:
1. federalrunner_list_wizards() - List available wizards
2. federalrunner_get_wizard_info() - Get wizard schema (THE CONTRACT)
3. federalrunner_execute_wizard() - Execute wizard with user data

Two-phase testing strategy for execute_wizard:
- Phase 1: Non-headless Chromium (visual debugging) - RUN THIS FIRST
- Phase 2: Headless WebKit (production validation) - RUN AFTER Phase 1 passes

These tests validate LOCAL execution. Remote (Cloud Run) tests will be added
after server.py is implemented with OAuth 2.1 authentication.
"""

import pytest
import asyncio
from pathlib import Path
import sys

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from execution_tools import (
    federalrunner_list_wizards,
    federalrunner_get_wizard_info,
    federalrunner_execute_wizard
)


# ============================================================================
# TEST DATA - Valid FSA User Data (matches fsa-estimator-schema.json)
# ============================================================================

FSA_TEST_DATA = {
    # Page 1: Student Information
    "birth_month": "05",
    "birth_day": "15",
    "birth_year": "2007",
    "marital_status": "unmarried",
    "state": "Illinois",
    "grade_level": "freshman",

    # Page 2: Student Personal Circumstances
    "has_dependents": "no",
    "circumstance_none": True,

    # Page 3: Parent Marital Status
    "parents_married": "yes",

    # Page 4: Parent Information
    "parent_marital_status": "married",
    "parent_state": "Illinois",

    # Page 5: Family Size
    "family_size": 4,

    # Page 6: Parent Income and Assets
    "parent_filed_taxes": "yes",
    "parent_income": 85000,
    "parent_assets": 12000,
    "parent_child_support": 0,

    # Page 7: Student Income and Assets
    "student_filed_taxes": "no"
}


# ============================================================================
# MCP TOOL TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_federalrunner_list_wizards():
    """
    Test MCP Tool: federalrunner_list_wizards()

    This tool will be exposed via HTTP endpoint for Claude to call.
    It lists all discovered wizards available for execution.
    """
    result = await federalrunner_list_wizards()

    # Validate response structure
    assert result['success'] is True, f"Tool failed: {result.get('error')}"
    assert 'wizards' in result, "Response missing 'wizards' field"
    assert 'count' in result, "Response missing 'count' field"
    assert result['count'] > 0, "No wizards found"

    # Validate FSA wizard is in the list
    fsa_wizard = next((w for w in result['wizards'] if w['wizard_id'] == 'fsa-estimator'), None)
    assert fsa_wizard is not None, "FSA wizard not found in list"
    assert fsa_wizard['name'] == 'FSA Student Aid Estimator'
    assert fsa_wizard['total_pages'] == 7
    assert 'discovered_at' in fsa_wizard

    print(f"\n✅ PASSED: list_wizards found {result['count']} wizard(s)")
    print(f"   FSA Wizard: {fsa_wizard['name']} ({fsa_wizard['total_pages']} pages)")


@pytest.mark.asyncio
async def test_federalrunner_get_wizard_info():
    """
    Test MCP Tool: federalrunner_get_wizard_info()

    This tool will be exposed via HTTP endpoint for Claude to call.
    It returns THE SCHEMA (the contract) that Claude uses to collect user data.

    This is the critical contract-first pattern - Claude reads the schema
    to understand what data to collect from users.
    """
    result = await federalrunner_get_wizard_info("fsa-estimator")

    # Validate response structure
    assert result['success'] is True, f"Tool failed: {result.get('error')}"
    assert result['wizard_id'] == 'fsa-estimator'
    assert 'schema' in result, "Response missing 'schema' field"

    # Validate schema structure (JSON Schema draft-07)
    schema = result['schema']
    assert '$schema' in schema, "Schema missing $schema field"
    assert 'properties' in schema, "Schema missing properties"
    assert 'required' in schema, "Schema missing required fields"

    # Validate schema has Claude hints
    assert '_claude_hints' in schema, "Schema missing Claude hints"
    assert '_example_user_data' in schema, "Schema missing example data"

    # Validate key field_ids are in schema
    assert 'birth_month' in schema['properties']
    assert 'marital_status' in schema['properties']
    assert 'state' in schema['properties']

    print(f"\n✅ PASSED: get_wizard_info returned schema for {result['wizard_id']}")
    print(f"   Schema properties: {len(schema['properties'])}")
    print(f"   Required fields: {len(schema['required'])}")


@pytest.mark.asyncio
@pytest.mark.slow
async def test_federalrunner_execute_wizard_non_headless():
    """
    Test MCP Tool: federalrunner_execute_wizard() [NON-HEADLESS MODE]

    This is THE MAIN TOOL - what Claude actually calls to execute wizards.

    Non-headless Chromium execution (VISUAL DEBUGGING)
    - Watch the browser fill out the FSA form step by step
    - Perfect for debugging and verifying field interactions

    This test uses configuration from .env file:
      FEDERALRUNNER_BROWSER_TYPE=chromium (recommended for visual debugging)
      FEDERALRUNNER_HEADLESS=false (shows browser window)
      FEDERALRUNNER_SLOW_MO=500 (slows down actions to watch)

    Tests the complete contract-first workflow:
    1. Load User Data Schema from wizards/data-schemas/
    2. Validate user_data against schema
    3. Load Wizard Structure from wizards/wizard-structures/
    4. Map field_id → selector (THE CRITICAL MAPPING)
    5. Execute atomically with Playwright
    """
    print("\n" + "="*70)
    print("🔵 Non-Headless Chromium Execution (Visual Debugging)")
    print("   Watch the browser execute the FSA wizard visually")
    print("   Configuration loaded from .env file")
    print("="*70 + "\n")

    # Execute wizard using the MCP tool (what Claude calls!)
    # Config loads from .env file automatically
    result = await federalrunner_execute_wizard(
        wizard_id="fsa-estimator",
        user_data=FSA_TEST_DATA
    )

    # Validate response
    assert result['success'] is True, f"Execution failed: {result.get('error')}"
    assert result['wizard_id'] == 'fsa-estimator'
    assert result['pages_completed'] == 7, f"Expected 7 pages, got {result['pages_completed']}"
    assert len(result['screenshots']) > 0, "No screenshots captured"
    assert result['execution_time_ms'] > 0

    print("\n" + "="*70)
    print(f"✅ PHASE 1 PASSED")
    print(f"   Wizard: {result['wizard_id']}")
    print(f"   Execution time: {result['execution_time_ms']}ms")
    print(f"   Pages completed: {result['pages_completed']}/7")
    print(f"   Screenshots: {len(result['screenshots'])}")
    print("="*70 + "\n")


@pytest.mark.asyncio
@pytest.mark.slow
async def test_federalrunner_execute_wizard_headless():
    """
    Test MCP Tool: federalrunner_execute_wizard() [HEADLESS MODE]

    Headless WebKit execution (PRODUCTION MODE)
    - No visible browser window
    - WebKit browser (FSA-compatible in headless mode)
    - Validates production configuration

    This test explicitly overrides configuration to run in headless mode,
    regardless of .env settings. This validates the configuration that will
    be used in Cloud Run deployment.
    """
    print("\n" + "="*70)
    print("🌐 Headless WebKit Execution (Production)")
    print("   Testing production-ready headless execution")
    print("="*70 + "\n")

    # Override configuration for headless execution
    import os
    original_browser = os.environ.get('FEDERALRUNNER_BROWSER_TYPE')
    original_headless = os.environ.get('FEDERALRUNNER_HEADLESS')
    original_slow_mo = os.environ.get('FEDERALRUNNER_SLOW_MO')

    try:
        # Set headless configuration
        os.environ['FEDERALRUNNER_BROWSER_TYPE'] = 'webkit'
        os.environ['FEDERALRUNNER_HEADLESS'] = 'true'
        os.environ['FEDERALRUNNER_SLOW_MO'] = '0'

        # Reload config to pick up new environment variables
        from config import reload_config
        reload_config()

        # Execute wizard
        result = await federalrunner_execute_wizard(
            wizard_id="fsa-estimator",
            user_data=FSA_TEST_DATA
        )
    finally:
        # Restore original environment variables
        if original_browser is not None:
            os.environ['FEDERALRUNNER_BROWSER_TYPE'] = original_browser
        elif 'FEDERALRUNNER_BROWSER_TYPE' in os.environ:
            del os.environ['FEDERALRUNNER_BROWSER_TYPE']

        if original_headless is not None:
            os.environ['FEDERALRUNNER_HEADLESS'] = original_headless
        elif 'FEDERALRUNNER_HEADLESS' in os.environ:
            del os.environ['FEDERALRUNNER_HEADLESS']

        if original_slow_mo is not None:
            os.environ['FEDERALRUNNER_SLOW_MO'] = original_slow_mo
        elif 'FEDERALRUNNER_SLOW_MO' in os.environ:
            del os.environ['FEDERALRUNNER_SLOW_MO']

        # Reload config to restore original settings
        reload_config()

    # Validate response
    assert result['success'] is True, f"Execution failed: {result.get('error')}"
    assert result['wizard_id'] == 'fsa-estimator'
    assert result['pages_completed'] == 7, f"Expected 7 pages, got {result['pages_completed']}"

    print("\n" + "="*70)
    print(f"✅ PHASE 2 PASSED")
    print(f"   Wizard: {result['wizard_id']}")
    print(f"   Execution time: {result['execution_time_ms']}ms")
    print(f"   Pages completed: {result['pages_completed']}/7")
    print(f"   Screenshots: {len(result['screenshots'])}")
    print("="*70 + "\n")


# ============================================================================
# ERROR HANDLING TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_execute_wizard_validation_failure():
    """
    Test that invalid user_data is caught before execution.

    The schema validator should reject invalid data and return helpful errors
    to guide Claude in collecting the correct data.
    """
    invalid_data = {
        "birth_month": "13",  # Invalid - doesn't match pattern
        "birth_year": "2007"
        # Missing most required fields
    }

    result = await federalrunner_execute_wizard(
        wizard_id="fsa-estimator",
        user_data=invalid_data
    )

    # Should fail validation
    assert result['success'] is False
    assert 'validation_errors' in result
    assert result['error'] == 'User data validation failed'

    print("\n✅ PASSED: Validation failure caught before execution")
    print(f"   Error: {result['error']}")


@pytest.mark.asyncio
async def test_execute_wizard_nonexistent_wizard():
    """
    Test error handling for non-existent wizard.

    Should return helpful error message when wizard doesn't exist.
    """
    result = await federalrunner_execute_wizard(
        wizard_id="nonexistent-wizard",
        user_data=FSA_TEST_DATA
    )

    # Should fail with helpful error
    assert result['success'] is False
    assert 'error' in result
    assert 'nonexistent-wizard' in result['error'].lower() or 'not found' in result['error'].lower()

    print("\n✅ PASSED: Non-existent wizard error handled gracefully")
    print(f"   Error: {result['error']}")
