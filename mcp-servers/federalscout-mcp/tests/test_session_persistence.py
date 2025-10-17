"""
Test session persistence across multiple tool calls.

End-to-end test that simulates how Claude Desktop interacts with FederalScout,
verifying that:
1. Sessions persist in _active_sessions global dictionary
2. Browser state is maintained between tool calls
3. Browser doesn't close until federalscout_complete_discovery is called
4. Session cleanup works correctly

Run with: pytest tests/test_session_persistence.py -v
"""

import asyncio
import json
import logging
import sys
from pathlib import Path

import pytest

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from discovery_tools import (
    federalscout_start_discovery,
    federalscout_click_element,
    federalscout_execute_actions,
    federalscout_get_page_info,
    federalscout_save_page_metadata,
    federalscout_complete_discovery,
    federalscout_save_schema,
    _active_sessions,
    _get_session
)

# Test logger
logger = logging.getLogger('federalscout.test')


class TestSessionPersistence:
    """End-to-end test for session persistence through full workflow."""

    @pytest.mark.asyncio
    async def test_end_to_end_session_persistence(self, test_config):
        """
        End-to-end session persistence test covering:
        - Session persistence across all tool calls
        - Universal batch actions (federalscout_execute_actions)
        - Proper cleanup on completion

        This simulates real Claude Desktop usage patterns.
        """
        logger.info("\n" + "=" * 80)
        logger.info("END-TO-END SESSION PERSISTENCE TEST")
        logger.info("=" * 80)

        # Start discovery (creates session)
        logger.info("\n📍 Starting discovery session...")
        result = await federalscout_start_discovery("https://studentaid.gov/aid-estimator/")
        assert result['success'] is True, "Start discovery should succeed"

        session_id = result['session_id']
        logger.info(f"✓ Session created: {session_id}")

        # Verify session exists in global dictionary
        assert session_id in _active_sessions, "Session should be in _active_sessions"
        session1 = _get_session(session_id)
        assert session1 is not None, "Session should be retrievable"
        browser_instance = session1.client.browser
        page_instance = session1.client.page
        logger.info(f"✓ Session verified - Browser ID: {id(browser_instance)}, Page ID: {id(page_instance)}")

        # Click element (session should persist)
        logger.info("\n📍 Clicking 'Start Estimate'...")
        await asyncio.sleep(1)
        result = await federalscout_click_element(session_id, "Start Estimate", "text")
        assert result['success'] is True, "Click should succeed"

        session2 = _get_session(session_id)
        assert session2 is session1, "Should be same session instance"
        assert session2.client.browser is browser_instance, "Should be same browser instance"
        logger.info(f"✓ Session persisted after click - Same browser: {session2.client.browser is browser_instance}")

        # Execute batch actions (session should persist)
        logger.info("\n📍 Executing batch actions (5 diverse actions)...")
        await asyncio.sleep(1)

        actions = [
            {"action": "fill", "selector": "#fsa_Input_DateOfBirthMonth", "value": "05"},
            {"action": "fill", "selector": "#fsa_Input_DateOfBirthDay", "value": "15"},
            {"action": "fill", "selector": "#fsa_Input_DateOfBirthYear", "value": "2007"},
            {"action": "javascript_click", "selector": "#fsa_Radio_MaritalStatusUnmarried"},
            {"action": "fill_enter", "selector": "#fsa_Typeahead_StateOfResidence", "value": "Illinois"},
        ]

        result = await federalscout_execute_actions(session_id, actions)
        assert result['success'] is True
        assert result['completed_count'] == 5

        session3 = _get_session(session_id)
        assert session3 is session1, "Session should persist after execute_actions"
        logger.info(f"✓ Session persisted after batch actions ({result['completed_count']} actions)")

        # Wait for conditional field to appear
        logger.info("  Waiting for conditional field...")
        await asyncio.sleep(1)

        # Execute conditional action
        actions_conditional = [
            {"action": "javascript_click", "selector": "#fsa_Radio_CollegeLevelFreshman"},
        ]

        result = await federalscout_execute_actions(session_id, actions_conditional)
        assert result['success'] is True
        session4 = _get_session(session_id)
        assert session4 is session1, "Session should persist after conditional action"
        logger.info("✓ Session persisted after conditional field handling")

        # Get page info (session should persist)
        logger.info("\n📍 Getting page info...")
        await asyncio.sleep(1)
        result = await federalscout_get_page_info(session_id)
        assert result['success'] is True, "Get page info should succeed"

        session5 = _get_session(session_id)
        assert session5 is session1, "Session should persist after get_page_info"
        logger.info("✓ Session persisted after get_page_info")

        # Save page metadata (session should persist)
        logger.info("\n📍 Saving page metadata...")
        await asyncio.sleep(1)

        page_metadata = {
            "page_number": 1,
            "page_title": "Student Information",
            "url_pattern": result.get('current_url'),
            "fields": [
                {"label": "Birth Month", "field_id": "birth_month", "selector": "#fsa_Input_DateOfBirthMonth",
                 "field_type": "number", "interaction": "fill", "required": True, "example_value": "05"},
                {"label": "Birth Day", "field_id": "birth_day", "selector": "#fsa_Input_DateOfBirthDay",
                 "field_type": "number", "interaction": "fill", "required": True, "example_value": "15"},
                {"label": "Birth Year", "field_id": "birth_year", "selector": "#fsa_Input_DateOfBirthYear",
                 "field_type": "number", "interaction": "fill", "required": True, "example_value": "2007"},
                {"label": "Marital Status", "field_id": "marital_status", "selector": "#fsa_Radio_MaritalStatusUnmarried",
                 "field_type": "radio", "interaction": "javascript_click", "required": True, "example_value": "unmarried"},
                {"label": "State", "field_id": "state", "selector": "#fsa_Typeahead_StateOfResidence",
                 "field_type": "typeahead", "interaction": "fill_enter", "required": True, "example_value": "Illinois"},
                {"label": "Grade Level", "field_id": "grade", "selector": "#fsa_Radio_CollegeLevelFreshman",
                 "field_type": "radio", "interaction": "javascript_click", "required": True, "example_value": "freshman"}
            ],
            "continue_button": {"text": "Continue", "selector": "button:has-text('Continue')"}
        }

        result = await federalscout_save_page_metadata(session_id, page_metadata)
        assert result['success'] is True, "Save page metadata should succeed"

        session6 = _get_session(session_id)
        assert session6 is session1, "Session should persist after save_page_metadata"
        logger.info("✓ Session persisted after save_page_metadata")

        # Verify browser still connected before completion
        logger.info("\n📍 Verifying browser state before completion...")
        await asyncio.sleep(1)
        assert session1.client.browser.is_connected(), "Browser should still be connected"
        current_url = await session1.client.get_current_url()
        logger.info(f"✓ Browser connected - URL: {current_url[:50]}...")

        # Complete discovery (should cleanup session)
        logger.info("\n📍 Completing discovery...")
        await asyncio.sleep(1)

        result = await federalscout_complete_discovery(
            session_id=session_id,
            wizard_name="Session Persistence Test",
            wizard_id="session-persistence-test",
            start_action={
                "description": "Click 'Start Estimate' button",
                "selector": "Start Estimate",
                "selector_type": "text"
            }
        )
        assert result['success'] is True, f"Complete discovery should succeed: {result.get('error', '')}"
        logger.info(f"✓ Discovery completed: {result['saved_to']}")

        # Verify wizard validates against Universal Schema (Contract-First pattern)
        with open(result['saved_to'], 'r') as f:
            wizard_data = json.load(f)

        universal_schema_path = Path(__file__).parent.parent.parent.parent / "schemas" / "wizard-structure-v1.schema.json"
        if universal_schema_path.exists():
            from jsonschema import validate as json_schema_validate
            with open(universal_schema_path, 'r') as f:
                universal_schema = json.load(f)
            json_schema_validate(wizard_data, universal_schema)
            logger.info("✓ Wizard structure validates against Universal Schema (Contract-First pattern)")

        # Generate User Data Schema (THE CONTRACT)
        logger.info("\n📍 Generating User Data Schema...")
        user_data_schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "title": "Session Persistence Test - User Data",
            "description": "User data schema for session persistence test",
            "type": "object",
            "required": ["birth_month", "birth_day", "birth_year", "marital_status", "state", "grade"],
            "properties": {
                "birth_month": {"type": "string", "pattern": "^(0[1-9]|1[0-2])$"},
                "birth_day": {"type": "string", "pattern": "^(0[1-9]|[12][0-9]|3[01])$"},
                "birth_year": {"type": "string", "pattern": "^[0-9]{4}$"},
                "marital_status": {"type": "string", "enum": ["married", "unmarried"]},
                "state": {"type": "string"},
                "grade": {"type": "string", "enum": ["freshman", "sophomore", "junior", "senior", "graduate"]}
            }
        }
        schema_result = await federalscout_save_schema("session-persistence-test", user_data_schema)
        assert schema_result['success'] is True
        logger.info("✓ User Data Schema saved (Contract-First pattern)")

        # Verify session cleanup
        assert session_id not in _active_sessions, "Session should be removed from _active_sessions"
        assert _get_session(session_id, silent=True) is None, "Session should no longer be retrievable"
        assert not browser_instance.is_connected(), "Browser should be disconnected"
        logger.info("✓ Session cleaned up correctly")
        logger.info("✓ Browser closed")

        # ═══════════════════════════════════════════════════════════════════
        # SUCCESS SUMMARY
        # ═══════════════════════════════════════════════════════════════════

        logger.info("\n" + "=" * 80)
        logger.info("✓ END-TO-END TEST PASSED")
        logger.info("=" * 80)
        logger.info("\nWhat was tested:")
        logger.info("  ✓ Session creation and persistence")
        logger.info("  ✓ Browser instance reuse across 7 tool calls (including schema)")
        logger.info("  ✓ Batch actions (federalscout_execute_actions) with session persistence")
        logger.info("  ✓ Conditional field handling with session persistence")
        logger.info("  ✓ Page metadata saving with session persistence")
        logger.info("  ✓ User data schema generation (Contract-First pattern)")
        logger.info("  ✓ Proper cleanup on completion")
        logger.info("\nKey validations:")
        logger.info("  - Same browser instance used throughout session")
        logger.info("  - Session properly removed from _active_sessions on completion")
        logger.info("  - Browser properly closed on completion")
        logger.info("=" * 80)


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "-s", "--tb=short"])
