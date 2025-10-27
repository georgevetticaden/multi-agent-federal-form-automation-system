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

Uses proper logging instead of print statements (matches FederalScout pattern).
"""

import pytest
import asyncio
import logging
from pathlib import Path
import sys
import time

# Add parent directory to path so we can import src as a package
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.execution_tools import (
    federalrunner_list_wizards,
    federalrunner_get_wizard_info,
    federalrunner_execute_wizard
)

# Test logger
logger = logging.getLogger('federalrunner.test')


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
    "personal_circumstances_none": True,

    # Page 3: Parent Marital Status
    "parents_married": "yes",

    # Page 4: Parent Information
    "parent_marital_status": "married",
    "parent_state": "Illinois",

    # Page 5: Family Size
    "family_size": 4,

    # Page 6: Parent Income and Assets
    "parent_filed_taxes": "yes",
    "parent_income": "85000",
    "parent_assets": "50000",
    "parent_child_support": "0",

    # Page 7: Student Income and Assets
    "student_filed_taxes": "no"
}

# ============================================================================
# TEST DATA - Valid Loan Simulator User Data (matches loan-simulator-borrow-more-schema.json)
# ============================================================================

LOAN_SIMULATOR_TEST_DATA = {
    # Page 1: Enrollment Information
    "program_timing": "future",

    # Page 2: Program Information (TESTS UNICODE!)
    "program_type": "Bachelor's degree",  # Unicode apostrophe test
    "program_length": "4 years",
    "dependency_status": "dependent",
    "school_location": "Illinois",
    "school_name": "University of Illinois",

    # Page 3: Family Income
    "family_income": "$75,000 - $110,000",

    # Page 4: Borrowing Amount
    "borrow_amount": 30000,

    # Page 5: Expected Salary
    "expected_salary": 55000,
    "income_growth_rate": 3,

    # Page 6: Current Loans (TESTS REPEATABLE FIELD / ARRAY HANDLING)
    # Simulating a student who already has some loans and wants to borrow more
    # This tests the "Add a Loan" workflow: click Add → fill fields → click Save → repeat
    "current_loans": [
        {
            "loan_type": "Direct Subsidized Loan",
            "loan_interest_rate": 6.39,
            "loan_balance": 10000
        },
        {
            "loan_type": "Direct PLUS Loan for Graduate/Professionals",
            "loan_interest_rate": 8.94,
            "loan_balance": 40000
        }
    ]
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

    # Validate Loan Simulator wizard is in the list
    loan_wizard = next((w for w in result['wizards'] if w['wizard_id'] == 'loan-simulator-borrow-more'), None)
    assert loan_wizard is not None, "Loan Simulator wizard not found in list"
    assert 'Loan Simulator' in loan_wizard['name']
    assert loan_wizard['total_pages'] == 6
    assert 'discovered_at' in loan_wizard

    logger.info(f"✅ PASSED: list_wizards found {result['count']} wizard(s)")
    logger.info(f"   FSA Wizard: {fsa_wizard['name']} ({fsa_wizard['total_pages']} pages)")
    logger.info(f"   Loan Simulator: {loan_wizard['name']} ({loan_wizard['total_pages']} pages)")


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

    logger.info(f"✅ PASSED: get_wizard_info returned schema for {result['wizard_id']}")
    logger.info(f"   Schema properties: {len(schema['properties'])}")
    logger.info(f"   Required fields: {len(schema['required'])}")


@pytest.mark.asyncio
@pytest.mark.slow
async def test_federalrunner_execute_wizard_non_headless(test_config):
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

    Screenshots are saved to: tests/test_output/screenshots/
    """
    logger.info("\n" + "="*70)
    logger.info("🔵 Non-Headless Chromium Execution (Visual Debugging)")
    logger.info("   Watch the browser execute the FSA wizard visually")
    logger.info("   Configuration loaded from .env file")
    logger.info(f"   Screenshots will be saved to: {test_config.screenshot_dir}")
    logger.info("="*70 + "\n")

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

    logger.info("\n" + "="*70)
    logger.info(f"✅ NON-HEADLESS TEST PASSED")
    logger.info(f"   Wizard: {result['wizard_id']}")
    logger.info(f"   Execution time: {result['execution_time_ms']}ms")
    logger.info(f"   Pages completed: {result['pages_completed']}/7")
    logger.info(f"   Screenshots: {len(result['screenshots'])}")
    logger.info("="*70 + "\n")


@pytest.mark.asyncio
@pytest.mark.slow
async def test_federalrunner_execute_wizard_headless(test_config):
    """
    Test MCP Tool: federalrunner_execute_wizard() [HEADLESS MODE]

    Headless WebKit execution (PRODUCTION MODE)
    - No visible browser window
    - WebKit browser (FSA-compatible in headless mode)
    - Validates production configuration

    This test explicitly overrides configuration to run in headless mode,
    regardless of .env settings. This validates the configuration that will
    be used in Cloud Run deployment.

    Screenshots are saved to: tests/test_output/screenshots/
    """
    logger.info("\n" + "="*70)
    logger.info("🌐 Headless WebKit Execution (Production)")
    logger.info("   Testing production-ready headless execution")
    logger.info(f"   Screenshots will be saved to: {test_config.screenshot_dir}")
    logger.info("="*70 + "\n")

    # Override configuration for headless execution
    # Use the same pattern as non-headless tests: modify the global config directly
    from src.config import get_config, set_config

    # Save original config
    original_config = get_config()

    try:
        # Create a new config with headless settings (keep test screenshot_dir!)
        headless_config = original_config.model_copy(update={
            'browser_type': 'webkit',
            'headless': True,
            'slow_mo': 0,
            # Keep the test screenshot directory from the fixture
            'screenshot_dir': test_config.screenshot_dir,
            'log_dir': test_config.log_dir
        })

        # Set the modified config globally
        set_config(headless_config)

        # Execute wizard
        result = await federalrunner_execute_wizard(
            wizard_id="fsa-estimator",
            user_data=FSA_TEST_DATA
        )
    finally:
        # Restore original config
        set_config(original_config)

    # Validate response
    assert result['success'] is True, f"Execution failed: {result.get('error')}"
    assert result['wizard_id'] == 'fsa-estimator'
    assert result['pages_completed'] == 7, f"Expected 7 pages, got {result['pages_completed']}"

    logger.info("\n" + "="*70)
    logger.info(f"✅ HEADLESS TEST PASSED")
    logger.info(f"   Wizard: {result['wizard_id']}")
    logger.info(f"   Execution time: {result['execution_time_ms']}ms")
    logger.info(f"   Pages completed: {result['pages_completed']}/7")
    logger.info(f"   Screenshots: {len(result['screenshots'])}")
    logger.info("="*70 + "\n")


@pytest.mark.asyncio
@pytest.mark.slow
async def test_loan_simulator_execute_wizard_non_headless(test_config):
    """
    Test MCP Tool: federalrunner_execute_wizard() for Loan Simulator [NON-HEADLESS MODE]

    Tests the Loan Simulator "Borrow More" wizard execution.
    This wizard tests:
    - Unicode dropdown handling (Bachelor's degree with smart quote)
    - Optional fields (school_location, school_name)
    - Array fields (current_loans - can be empty)
    - Number fields (borrow_amount, expected_salary, income_growth_rate)
    - Enum dropdowns (program_type, program_length, dependency_status, family_income)

    Non-headless Chromium execution (VISUAL DEBUGGING)
    - Watch the browser fill out the Loan Simulator form step by step
    - Perfect for debugging and verifying the Unicode fix works

    This test uses configuration from .env file:
      FEDERALRUNNER_BROWSER_TYPE=chromium (recommended for visual debugging)
      FEDERALRUNNER_HEADLESS=false (shows browser window)
      FEDERALRUNNER_SLOW_MO=500 (slows down actions to watch)

    Wizard structure:
    - Total pages: 6
    - Tests Unicode handling in dropdown options (Bachelor's degree)
    - Tests optional typeahead fields (school location/name)
    - Tests array fields (current loans - empty array in this test)

    Screenshots are saved to: tests/test_output/screenshots/
    """
    logger.info("\n" + "="*70)
    logger.info("🔵 Loan Simulator - Non-Headless Chromium Execution (Visual Debugging)")
    logger.info("   Watch the browser execute the Loan Simulator wizard visually")
    logger.info("   Testing: Unicode dropdowns, optional fields, arrays")
    logger.info(f"   Screenshots will be saved to: {test_config.screenshot_dir}")
    logger.info("="*70 + "\n")

    # Execute wizard using the MCP tool (what Claude calls!)
    # Config loads from .env file automatically
    result = await federalrunner_execute_wizard(
        wizard_id="loan-simulator-borrow-more",
        user_data=LOAN_SIMULATOR_TEST_DATA
    )

    # Validate response
    assert result['success'] is True, f"Execution failed: {result.get('error')}"
    assert result['wizard_id'] == 'loan-simulator-borrow-more'
    assert result['pages_completed'] == 6, f"Expected 6 pages, got {result['pages_completed']}"
    assert len(result['screenshots']) > 0, "No screenshots captured"
    assert result['execution_time_ms'] > 0

    logger.info("\n" + "="*70)
    logger.info(f"✅ LOAN SIMULATOR NON-HEADLESS TEST PASSED")
    logger.info(f"   Wizard: {result['wizard_id']}")
    logger.info(f"   Execution time: {result['execution_time_ms']}ms")
    logger.info(f"   Pages completed: {result['pages_completed']}/6")
    logger.info(f"   Screenshots: {len(result['screenshots'])}")
    logger.info(f"   Unicode handling: ✅ Bachelor's degree selected successfully")
    logger.info("="*70 + "\n")


@pytest.mark.asyncio
@pytest.mark.slow
async def test_loan_simulator_execute_wizard_headless(test_config):
    """
    Test MCP Tool: federalrunner_execute_wizard() for Loan Simulator [HEADLESS MODE]

    Headless WebKit execution (PRODUCTION MODE)
    - No visible browser window
    - WebKit browser (FSA-compatible in headless mode)
    - Validates production configuration with all optimizations

    This test explicitly overrides configuration to run in headless mode,
    regardless of .env settings. This validates the EXACT configuration
    that will be used in Cloud Run deployment.

    Tests production performance with:
    - Unicode dropdown handling (optimized 5s timeout)
    - Repeatable field workflow (Add a Loan)
    - WebKit headless (production browser)
    - Fast execution (<30 seconds target)

    Screenshots are saved to: tests/test_output/screenshots/
    """
    logger.info("\n" + "="*70)
    logger.info("🌐 Loan Simulator - Headless WebKit Execution (Production)")
    logger.info("   Testing production-ready headless execution")
    logger.info("   Unicode handling + Repeatable fields + WebKit")
    logger.info(f"   Screenshots will be saved to: {test_config.screenshot_dir}")
    logger.info("="*70 + "\n")

    # Override configuration for headless execution
    # Use the same pattern as non-headless tests: modify the global config directly
    from src.config import get_config, set_config

    # Save original config
    original_config = get_config()

    try:
        # Create a new config with headless settings (keep test screenshot_dir!)
        headless_config = original_config.model_copy(update={
            'browser_type': 'webkit',
            'headless': True,
            'slow_mo': 0,
            # Keep the test screenshot directory from the fixture
            'screenshot_dir': test_config.screenshot_dir,
            'log_dir': test_config.log_dir
        })

        # Set the modified config globally
        set_config(headless_config)

        # Execute wizard
        result = await federalrunner_execute_wizard(
            wizard_id="loan-simulator-borrow-more",
            user_data=LOAN_SIMULATOR_TEST_DATA
        )
    finally:
        # Restore original config
        set_config(original_config)

    # Validate response
    assert result['success'] is True, f"Execution failed: {result.get('error')}"
    assert result['wizard_id'] == 'loan-simulator-borrow-more'
    assert result['pages_completed'] == 6, f"Expected 6 pages, got {result['pages_completed']}"

    logger.info("\n" + "="*70)
    logger.info(f"✅ LOAN SIMULATOR HEADLESS TEST PASSED")
    logger.info(f"   Wizard: {result['wizard_id']}")
    logger.info(f"   Execution time: {result['execution_time_ms']}ms")
    logger.info(f"   Pages completed: {result['pages_completed']}/6")
    logger.info(f"   Screenshots: {len(result['screenshots'])}")
    logger.info(f"   Unicode handling: ✅ Optimized (5s timeout)")
    logger.info(f"   Repeatable fields: ✅ 2 loans added")
    logger.info(f"   Browser: WebKit (headless)")
    logger.info("="*70 + "\n")


@pytest.mark.asyncio
@pytest.mark.slow
async def test_federalrunner_execute_wizard_demo_recording(test_config):
    """
    Test MCP Tool: federalrunner_execute_wizard() [DEMO RECORDING MODE]

    SIMPLIFIED: Just like loan_simulator test - calls federalrunner_execute_wizard()!

    This test uses the EXACT dataset from the production demo recording.
    Non-headless Chromium execution with visible browser and slow_mo.

    Demo Data Profile:
    - Student: 17 years old, unmarried, no dependents, from Illinois
    - Grade: Freshman (fall 2026)
    - Family: 5 members, parents married
    - Parent income: $200,000
    - Parent assets: $100,000
    - Filed taxes: Parents yes, Student no

    Usage for Demo Recording:
    1. Set up your .env file:
       FEDERALRUNNER_BROWSER_TYPE=chromium
       FEDERALRUNNER_HEADLESS=false
       FEDERALRUNNER_SLOW_MO=500  (adjust speed for recording)

    2. Position your recording frame (browser opens in same spot each time)

    3. Start your screen recording software

    4. Run the test:
       cd mcp-servers/federalrunner-mcp
       pytest tests/test_execution_local.py::test_federalrunner_execute_wizard_demo_recording -v -s

    5. Browser launches and executes the wizard automatically

    Tip: Run once to see browser position, then adjust your recording frame.

    Screenshots are saved to: tests/test_output/screenshots/
    """
    # Demo recording dataset (exact match from production demo)
    DEMO_DATA = {
        # Page 1: Student Information
        "birth_month": "05",
        "birth_day": "15",
        "birth_year": "2007",
        "marital_status": "unmarried",
        "state": "Illinois",
        "grade_level": "freshman",

        # Page 2: Student Personal Circumstances
        "has_dependents": "no",
        "personal_circumstances_none": True,

        # Page 3: Parent Marital Status
        "parents_married": "yes",

        # Page 4: Parent Information
        "parent_marital_status": "married",
        "parent_state": "Illinois",

        # Page 5: Family Size
        "family_size": 5,

        # Page 6: Parent Income and Assets
        "parent_filed_taxes": "yes",
        "parent_income": "200000",
        "parent_assets": "100000",
        "parent_child_support": "0",

        # Page 7: Student Income and Assets
        "student_filed_taxes": "no"
    }

    logger.info("\n" + "="*70)
    logger.info("🎬 FSA Demo - Non-Headless Chromium Execution (Visual Demo)")
    logger.info("   Watch the browser execute the FSA wizard visually")
    logger.info("   Demo Dataset: 17yo student, IL, 5-person family, $200K income")
    logger.info(f"   Screenshots will be saved to: {test_config.screenshot_dir}")
    logger.info(f"   Viewport: 1100px width (optimized for recording - from .env)")
    logger.info("="*70 + "\n")

    # Execute wizard using the MCP tool (what Claude calls!)
    # Config loads from .env file automatically (non-headless Chromium with slow_mo, 1100px viewport)
    result = await federalrunner_execute_wizard(
        wizard_id="fsa-estimator",
        user_data=DEMO_DATA
    )

    # Validate response
    assert result['success'] is True, f"Execution failed: {result.get('error')}"
    assert result['wizard_id'] == 'fsa-estimator'
    assert result['pages_completed'] == 7, f"Expected 7 pages, got {result['pages_completed']}"
    assert len(result['screenshots']) > 0, "No screenshots captured"
    assert result['execution_time_ms'] > 0

    logger.info("\n" + "="*70)
    logger.info(f"✅ FSA DEMO RECORDING TEST PASSED")
    logger.info(f"   Wizard: {result['wizard_id']}")
    logger.info(f"   Execution time: {result['execution_time_ms']}ms")
    logger.info(f"   Pages completed: {result['pages_completed']}/7")
    logger.info(f"   Screenshots: {len(result['screenshots'])}")
    logger.info("\n   🎥 Recording complete! Browser will stay open.")
    logger.info("="*70)

    # Keep browser window open for review
    logger.info("\n⏸️  Browser window is showing the final results page.")
    logger.info("   Review the results, then press Enter to close the browser and finish.\n")
    input("👉 Press Enter to close browser and finish test... ")


# ============================================================================
# ERROR HANDLING TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_execute_wizard_validation_failure():
    """
    Test that invalid user_data is caught before execution.

    The schema validator should reject invalid data and return helpful errors
    to guide Claude in collecting the correct data.

    Tests both missing fields and invalid field values.
    """
    # Test 1: Missing required fields
    invalid_data_missing = {
        "birth_month": "05",
        "birth_year": "2007"
        # Missing birth_day and other required fields
    }

    result = await federalrunner_execute_wizard(
        wizard_id="fsa-estimator",
        user_data=invalid_data_missing
    )

    assert result['success'] is False
    assert 'validation_errors' in result
    assert result['error'] == 'User data validation failed'
    assert len(result['validation_errors']['missing_fields']) > 0

    logger.info("✅ PASSED: Missing fields validation caught")
    logger.info(f"   Missing fields: {len(result['validation_errors']['missing_fields'])}")

    # Test 2: Invalid field values (all required fields present but some invalid)
    invalid_data_pattern = {
        **FSA_TEST_DATA,  # Start with valid data
        "birth_month": "13",  # Invalid - doesn't match pattern ^(0[1-9]|1[0-2])$
        "birth_day": "32"     # Invalid - doesn't match pattern ^(0[1-9]|[12][0-9]|3[01])$
    }

    result = await federalrunner_execute_wizard(
        wizard_id="fsa-estimator",
        user_data=invalid_data_pattern
    )

    assert result['success'] is False
    assert 'validation_errors' in result
    assert result['error'] == 'User data validation failed'
    assert len(result['validation_errors'].get('invalid_fields', [])) > 0

    logger.info("✅ PASSED: Invalid field values validation caught")
    logger.info(f"   Invalid fields: {len(result['validation_errors']['invalid_fields'])}")


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

    logger.info("✅ PASSED: Non-existent wizard error handled gracefully")
    logger.info(f"   Error: {result['error']}")


@pytest.mark.asyncio
@pytest.mark.slow
async def test_execute_wizard_runtime_error_with_screenshot():
    """
    Test runtime execution error with screenshot capture.

    🎯 VISUAL VALIDATION LOOP PATTERN (see requirements/reference/mdcalc/MDCalc-Blog.md)

    This test validates the same self-correcting pattern used in the MDCalc agent:

    1. Schema validation passes ✅ (type-safe contract upheld)
    2. Runtime execution fails ❌ (form shows validation error like "Select a response")
    3. Error screenshot captured 📸 (visual context of failure)
    4. Claude Vision analyzes screenshot + error message
    5. Claude guides user to correct the issue (e.g., "provide valid US state")
    6. Re-execute with corrected data

    From MDCalc blog: "The agent takes another screenshot to check for validation errors.
    This creates a self-correcting loop. The agent sees errors exactly as a human would
    and adapts on the fly. No error codes to parse, no API documentation to maintain—
    just visual understanding."

    Test scenario: International student currently studying abroad
    - Parent lives in: "California" (US state - valid)
    - Student currently in: "Kerala, India" (studying abroad)
    - User provides "Kerala, India" for student state field

    Schema validation: PASSES (state field accepts any string per schema)
    Runtime execution: FAILS (FSA form rejects "Kerala, India" - requires US state)
    Visual error: Screenshot shows "Select a response" validation message

    Expected behavior:
    - success: False
    - error: Contains helpful error message about field failure
    - screenshots: Includes error screenshot showing where execution failed
    - pages_completed < 7 (execution failed before completion)
    - Claude Vision can analyze screenshot + error to:
      1. See the "Select a response" validation error visually
      2. Understand FSA requires US state for legal residence
      3. Guide user: "For dependent students, use parent's state (California)"
      4. Re-execute with corrected data

    This is the universal pattern for form automation without APIs - visual intelligence
    that self-corrects based on what it sees, just like a human would.
    """
    logger.info("\n" + "="*70)
    logger.info("🔴 Runtime Execution Error Test (with Screenshot Capture)")
    logger.info("   Scenario: Student studying abroad in Kerala, India")
    logger.info("   Parent lives in California, USA")
    logger.info("   User incorrectly provides student's current location instead of legal residence")
    logger.info("="*70 + "\n")

    # Create test data that passes validation but fails at runtime
    # Realistic scenario: International student studying in India
    FSA_TEST_DATA_INVALID_STATE = {
        **FSA_TEST_DATA,
        "state": "Kerala, India",        # Student's CURRENT location (studying abroad)
        "parent_state": "California"     # Parent's US state (correct)
    }

    result = await federalrunner_execute_wizard(
        wizard_id="fsa-estimator",
        user_data=FSA_TEST_DATA_INVALID_STATE
    )

    # Pretty-print the full result for debugging
    import json
    logger.info("\n" + "="*70)
    logger.info("📋 Full execution result:")
    logger.info("="*70)
    # Create a copy without screenshots (too large to log)
    result_without_screenshots = {k: v for k, v in result.items() if k != 'screenshots'}
    result_without_screenshots['screenshots'] = f"<{len(result.get('screenshots', []))} screenshots captured>"
    logger.info(json.dumps(result_without_screenshots, indent=2))
    logger.info("="*70 + "\n")

    # Should fail at runtime (not validation)
    assert result['success'] is False, "Expected execution to fail with invalid state"
    assert 'error' in result, "Response missing 'error' field"
    assert 'error_type' in result, "Response missing 'error_type' field"

    # Should have captured screenshots (including error screenshot)
    assert 'screenshots' in result, "Response missing 'screenshots' field"
    assert len(result['screenshots']) > 0, "No screenshots captured (should have error screenshot)"

    # Should report which page it failed on
    assert 'pages_completed' in result
    # Should fail somewhere during execution (not complete all 7 pages)
    # Note: The actual failure may vary - typeahead might accept the value but cause issues later
    assert result['pages_completed'] < 7, f"Should fail before completing all pages, got {result['pages_completed']}"

    # Should have execution time
    assert 'execution_time_ms' in result
    assert result['execution_time_ms'] > 0

    logger.info("✅ PASSED: Runtime error captured with context")
    logger.info(f"   Error type: {result['error_type']}")
    logger.info(f"   Error message: {result['error']}")
    logger.info(f"   Pages completed before error: {result['pages_completed']}")
    logger.info(f"   Screenshots captured: {len(result['screenshots'])}")
    logger.info(f"   Execution time: {result['execution_time_ms']}ms")
    logger.info("\n   💡 Claude can use this error + screenshot to:")
    logger.info("      1. Show user the error screenshot")
    logger.info("      2. Analyze what went wrong (field selector, validation, etc.)")
    logger.info("      3. Provide guidance on correcting the input")
    logger.info("      4. Re-execute with corrected data")
    logger.info("\n   📝 Note: This test validates error recovery pattern:")
    logger.info("      - Data passes schema validation ✅")
    logger.info("      - Execution encounters runtime error ❌")
    logger.info("      - Error + screenshot captured for Claude to analyze 📸")
    logger.info("="*70 + "\n")
