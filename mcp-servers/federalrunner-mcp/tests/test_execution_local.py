"""
Local execution tests for FederalRunner.

Two-phase testing strategy:
1. Phase 1: Non-headless Chromium (visual debugging) - RUN THIS FIRST
2. Phase 2: Headless WebKit (production validation) - RUN AFTER Phase 1 passes

These tests use the real FSA wizard at studentaid.gov.
"""

import pytest
import asyncio
from pathlib import Path
import sys

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.config import FederalRunnerConfig
from src.models import WizardStructure
from src.schema_validator import SchemaValidator
from src.playwright_client import PlaywrightClient
from src.execution_tools import (
    federalrunner_list_wizards,
    federalrunner_get_wizard_info,
    federalrunner_execute_wizard
)


# ============================================================================
# TEST DATA - Valid FSA User Data
# ============================================================================

FSA_TEST_DATA_COMPLETE = {
    # Page 1: Student Information
    "birth_month": "05",
    "birth_day": "15",
    "birth_year": "2007",
    "marital_status": "unmarried",
    "state_of_residence": "Illinois",
    "grade_level": "freshman",

    # Page 2: Student Personal Circumstances
    "has_dependents": "no",
    "personal_circumstances": "none",

    # Page 3: Parent Marital Status
    "parents_married": "yes",

    # Page 4: Parent Information
    "parent_marital_status": "married",
    "parent_state_of_residence": "Illinois",

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
# UNIT TESTS - Individual Components
# ============================================================================

def test_schema_loading():
    """Test that we can load the FSA schema."""
    config = FederalRunnerConfig()
    validator = SchemaValidator(config)

    schema = validator.load_schema("fsa-estimator")

    assert schema is not None
    assert "$schema" in schema
    assert "properties" in schema
    assert "required" in schema
    assert "birth_month" in schema["properties"]

    print(" Schema loading test passed")


def test_schema_validation_valid_data():
    """Test that valid test data passes schema validation."""
    config = FederalRunnerConfig()
    validator = SchemaValidator(config)

    schema = validator.load_schema("fsa-estimator")
    result = validator.validate_user_data(FSA_TEST_DATA_COMPLETE, schema)

    assert result['valid'] is True

    print(" Schema validation (valid data) test passed")


def test_schema_validation_invalid_data():
    """Test that invalid data fails schema validation with helpful errors."""
    config = FederalRunnerConfig()
    validator = SchemaValidator(config)

    # Invalid: birth_month "13" doesn't match pattern
    invalid_data = {
        **FSA_TEST_DATA_COMPLETE,
        "birth_month": "13"  # Invalid month
    }

    schema = validator.load_schema("fsa-estimator")
    result = validator.validate_user_data(invalid_data, schema)

    assert result['valid'] is False
    assert 'error' in result
    assert len(result.get('invalid_fields', [])) > 0

    print(" Schema validation (invalid data) test passed")


def test_schema_validation_missing_required_fields():
    """Test that missing required fields are detected."""
    config = FederalRunnerConfig()
    validator = SchemaValidator(config)

    # Missing: birth_day (required field)
    incomplete_data = {
        "birth_month": "05",
        "birth_year": "2007"
        # Missing all other required fields
    }

    schema = validator.load_schema("fsa-estimator")
    result = validator.validate_user_data(incomplete_data, schema)

    assert result['valid'] is False
    assert 'error' in result

    print(" Schema validation (missing fields) test passed")


def test_wizard_structure_loading():
    """Test that we can load the FSA wizard structure."""
    config = FederalRunnerConfig()

    wizard_path = config.wizards_dir / "wizard-structures" / "fsa-estimator.json"
    wizard = WizardStructure.from_json_file(wizard_path)

    assert wizard.wizard_id == "fsa-estimator"
    assert wizard.name == "FSA Student Aid Estimator"
    assert wizard.total_pages == 7
    assert len(wizard.pages) == 7

    # Check that all pages have continue buttons
    for page in wizard.pages:
        assert page.continue_button is not None
        assert page.continue_button.selector is not None

    print(" Wizard structure loading test passed")


def test_field_id_to_selector_mapping():
    """Test that field_id correctly maps to selectors."""
    config = FederalRunnerConfig()

    wizard_path = config.wizards_dir / "wizard-structures" / "fsa-estimator.json"
    wizard = WizardStructure.from_json_file(wizard_path)

    # Test mapping logic (same as in execution_tools.py)
    field_values = {}
    user_data = FSA_TEST_DATA_COMPLETE

    for page in wizard.pages:
        for field in page.fields:
            field_id = field.field_id
            if field_id in user_data:
                field_values[field.selector] = user_data[field_id]

    # Verify some key mappings
    assert "#fsa_Input_DateOfBirthMonth" in field_values
    assert field_values["#fsa_Input_DateOfBirthMonth"] == "05"

    assert "#fsa_Radio_MaritalStatusUnmarried" in field_values
    assert field_values["#fsa_Radio_MaritalStatusUnmarried"] == "unmarried"

    print(f" Field mapping test passed - {len(field_values)} fields mapped")


# ============================================================================
# MCP TOOL TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_federalrunner_list_wizards():
    """Test the list_wizards MCP tool."""
    result = await federalrunner_list_wizards()

    assert result['success'] is True
    assert 'wizards' in result
    assert result['count'] > 0

    # Check FSA wizard is in the list
    fsa_wizard = next((w for w in result['wizards'] if w['wizard_id'] == 'fsa-estimator'), None)
    assert fsa_wizard is not None
    assert fsa_wizard['name'] == 'FSA Student Aid Estimator'

    print(f" list_wizards test passed - found {result['count']} wizard(s)")


@pytest.mark.asyncio
async def test_federalrunner_get_wizard_info():
    """Test the get_wizard_info MCP tool - returns THE SCHEMA."""
    result = await federalrunner_get_wizard_info("fsa-estimator")

    assert result['success'] is True
    assert result['wizard_id'] == 'fsa-estimator'
    assert 'schema' in result

    # Verify schema structure
    schema = result['schema']
    assert '$schema' in schema
    assert 'properties' in schema
    assert 'required' in schema

    # Check for Claude hints
    assert '_claude_hints' in schema
    assert '_example_user_data' in schema

    print(" get_wizard_info test passed - schema returned successfully")


# ============================================================================
# INTEGRATION TESTS - Playwright Execution
# ============================================================================

@pytest.mark.asyncio
@pytest.mark.slow
async def test_playwright_client_atomic_execution_non_headless():
    """
    PHASE 1: Non-headless Chromium execution (VISUAL DEBUGGING).

    RUN THIS FIRST to debug with visible browser!
    Watch the browser fill out the FSA form step by step.

    This test executes the FULL FSA wizard end-to-end.
    """
    print("\n" + "="*70)
    print("=5 PHASE 1: Non-Headless Chromium Execution")
    print("   Watch the browser execute the FSA wizard visually")
    print("="*70 + "\n")

    config = FederalRunnerConfig(
        headless=False,
        browser_type="chromium",
        slow_mo=500  # Slow down to 500ms per action so you can watch
    )

    # Load wizard structure
    wizard_path = config.wizards_dir / "wizard-structures" / "fsa-estimator.json"
    wizard = WizardStructure.from_json_file(wizard_path)

    # Map user_data (field_id) ’ field_values (selector)
    field_values = {}
    for page in wizard.pages:
        for field in page.fields:
            field_id = field.field_id
            if field_id in FSA_TEST_DATA_COMPLETE:
                field_values[field.selector] = FSA_TEST_DATA_COMPLETE[field_id]

    print(f"Mapped {len(field_values)} fields\n")

    # Execute atomically
    client = PlaywrightClient(config)
    result = await client.execute_wizard_atomically(wizard, field_values)

    # Assertions
    assert result['success'] is True, f"Execution failed: {result.get('error')}"
    assert result['pages_completed'] == 7, f"Expected 7 pages, got {result['pages_completed']}"
    assert len(result['screenshots']) > 0, "No screenshots captured"
    assert result['execution_time_ms'] > 0

    print("\n" + "="*70)
    print(f" PHASE 1 PASSED")
    print(f"   Execution time: {result['execution_time_ms']}ms")
    print(f"   Pages completed: {result['pages_completed']}/7")
    print(f"   Screenshots captured: {len(result['screenshots'])}")
    print("="*70 + "\n")


@pytest.mark.asyncio
@pytest.mark.slow
async def test_playwright_client_atomic_execution_headless():
    """
    PHASE 2: Headless WebKit execution (PRODUCTION MODE).

    RUN THIS AFTER Phase 1 passes!
    This validates the production configuration.

    WebKit is used because FSA website blocks headless Chromium.
    """
    print("\n" + "="*70)
    print("< PHASE 2: Headless WebKit Execution (Production)")
    print("   Testing production-ready headless execution")
    print("="*70 + "\n")

    config = FederalRunnerConfig(
        headless=True,
        browser_type="webkit"  # FSA-compatible in headless mode
    )

    # Load wizard structure
    wizard_path = config.wizards_dir / "wizard-structures" / "fsa-estimator.json"
    wizard = WizardStructure.from_json_file(wizard_path)

    # Map user_data (field_id) ’ field_values (selector)
    field_values = {}
    for page in wizard.pages:
        for field in page.fields:
            field_id = field.field_id
            if field_id in FSA_TEST_DATA_COMPLETE:
                field_values[field.selector] = FSA_TEST_DATA_COMPLETE[field_id]

    # Execute atomically
    client = PlaywrightClient(config)
    result = await client.execute_wizard_atomically(wizard, field_values)

    # Assertions
    assert result['success'] is True, f"Execution failed: {result.get('error')}"
    assert result['pages_completed'] == 7, f"Expected 7 pages, got {result['pages_completed']}"
    assert len(result['screenshots']) > 0, "No screenshots captured"

    print("\n" + "="*70)
    print(f" PHASE 2 PASSED")
    print(f"   Execution time: {result['execution_time_ms']}ms")
    print(f"   Pages completed: {result['pages_completed']}/7")
    print(f"   Screenshots captured: {len(result['screenshots'])}")
    print("="*70 + "\n")


# ============================================================================
# END-TO-END TEST - Complete MCP Tool Workflow
# ============================================================================

@pytest.mark.asyncio
@pytest.mark.slow
@pytest.mark.e2e
async def test_federalrunner_execute_wizard_e2e_non_headless():
    """
    END-TO-END TEST: Complete MCP tool workflow (Non-headless).

    This tests the FULL contract-first pattern:
    1. Load schema
    2. Validate user_data
    3. Map field_id ’ selector
    4. Execute with Playwright

    This is what Claude will actually call!
    """
    print("\n" + "="*70)
    print("<¯ END-TO-END TEST: federalrunner_execute_wizard()")
    print("   Testing complete contract-first workflow")
    print("="*70 + "\n")

    # Override config for visual debugging
    import os
    os.environ['FEDERALRUNNER_HEADLESS'] = 'false'
    os.environ['FEDERALRUNNER_BROWSER_TYPE'] = 'chromium'
    os.environ['FEDERALRUNNER_SLOW_MO'] = '300'

    # Execute wizard using the MCP tool (what Claude calls!)
    result = await federalrunner_execute_wizard(
        wizard_id="fsa-estimator",
        user_data=FSA_TEST_DATA_COMPLETE
    )

    # Assertions
    assert result['success'] is True, f"Execution failed: {result.get('error')}"
    assert result['wizard_id'] == 'fsa-estimator'
    assert result['pages_completed'] == 7
    assert len(result['screenshots']) > 0

    print("\n" + "="*70)
    print(f" END-TO-END TEST PASSED")
    print(f"   Wizard: {result['wizard_id']}")
    print(f"   Execution time: {result['execution_time_ms']}ms")
    print(f"   Pages completed: {result['pages_completed']}/7")
    print(f"   Screenshots: {len(result['screenshots'])}")
    print("="*70 + "\n")


@pytest.mark.asyncio
@pytest.mark.slow
@pytest.mark.e2e
async def test_federalrunner_execute_wizard_e2e_headless():
    """
    END-TO-END TEST: Complete MCP tool workflow (Headless).

    Production-ready test with headless WebKit.
    RUN AFTER non-headless test passes!
    """
    print("\n" + "="*70)
    print("<¯ END-TO-END TEST: federalrunner_execute_wizard() [HEADLESS]")
    print("   Testing production configuration")
    print("="*70 + "\n")

    # Override config for headless
    import os
    os.environ['FEDERALRUNNER_HEADLESS'] = 'true'
    os.environ['FEDERALRUNNER_BROWSER_TYPE'] = 'webkit'

    # Execute wizard
    result = await federalrunner_execute_wizard(
        wizard_id="fsa-estimator",
        user_data=FSA_TEST_DATA_COMPLETE
    )

    # Assertions
    assert result['success'] is True, f"Execution failed: {result.get('error')}"
    assert result['wizard_id'] == 'fsa-estimator'
    assert result['pages_completed'] == 7

    print("\n" + "="*70)
    print(f" END-TO-END HEADLESS TEST PASSED")
    print(f"   Execution time: {result['execution_time_ms']}ms")
    print(f"   Pages completed: {result['pages_completed']}/7")
    print("="*70 + "\n")


# ============================================================================
# ERROR HANDLING TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_execute_wizard_validation_failure():
    """Test that invalid user_data is caught before execution."""
    invalid_data = {
        "birth_month": "13",  # Invalid - doesn't match pattern
        "birth_year": "2007"
        # Missing most required fields
    }

    result = await federalrunner_execute_wizard(
        wizard_id="fsa-estimator",
        user_data=invalid_data
    )

    assert result['success'] is False
    assert 'validation_errors' in result

    print(" Validation failure test passed - errors caught before execution")


@pytest.mark.asyncio
async def test_execute_wizard_nonexistent_wizard():
    """Test error handling for non-existent wizard."""
    result = await federalrunner_execute_wizard(
        wizard_id="nonexistent-wizard",
        user_data=FSA_TEST_DATA_COMPLETE
    )

    assert result['success'] is False
    assert 'error' in result

    print(" Non-existent wizard test passed - error handled gracefully")
