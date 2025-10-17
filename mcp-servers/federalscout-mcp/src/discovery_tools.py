"""
FederalScout Discovery Tools - MCP tool implementations.

Implements 6 MCP tools for interactive wizard structure discovery:
1. federalscout_start_discovery - Begin discovery session
2. federalscout_click_element - Click elements on page
3. federalscout_execute_actions - Execute diverse actions in batch (fill, click, etc.)
4. federalscout_get_page_info - Extract detailed page information
5. federalscout_save_page_metadata - Save discovered page structure
6. federalscout_complete_discovery - Finish and save wizard structure

Reference: requirements/discovery/DISCOVERY_REQUIREMENTS.md REQ-DISC-004
Reference: requirements/shared/MCP_TOOL_SPECIFICATIONS.md
"""

import asyncio
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import time

from config import get_config, FederalScoutConfig
from logging_config import (
    get_logger,
    get_session_logger,
    log_tool_call,
    log_tool_result,
    log_session_event
)
from models import (
    WizardStructure,
    PageStructure,
    FieldStructure,
    ContinueButton,
    StartAction,
    SelectorType,
    InteractionType
)
from playwright_client import BrowserSession


logger = get_logger(__name__)


# Global session storage
_active_sessions: Dict[str, BrowserSession] = {}


def _cleanup_expired_sessions(config: FederalScoutConfig):
    """
    Clean up expired sessions.

    Args:
        config: FederalScout configuration with timeout settings
    """
    expired = []
    for session_id, session in _active_sessions.items():
        if session.is_expired(config.session_timeout):
            expired.append(session_id)
    
    for session_id in expired:
        session = _active_sessions.pop(session_id)
        asyncio.create_task(session.close())
        log_session_event(session_id, 'expired', logger=logger)
        logger.warning(f"Session expired and cleaned up: {session_id}")


def _get_session(session_id: str, silent: bool = False) -> Optional[BrowserSession]:
    """
    Get an active session by ID.

    Args:
        session_id: The session identifier
        silent: If True, don't log warnings when session not found (for cleanup validation)

    Returns:
        BrowserSession if found, None otherwise
    """
    session = _active_sessions.get(session_id)
    if session:
        logger.info(f"♻️  REUSING SESSION: {session_id}")
    else:
        if not silent:
            logger.warning(f"⚠️  SESSION NOT FOUND: {session_id}")
    return session


# Tool 1: Start Discovery
async def federalscout_start_discovery(url: str) -> Dict[str, Any]:
    """
    Begin wizard structure discovery session.
    
    Launches browser, navigates to URL, takes screenshot, and extracts
    initial HTML context.
    
    Args:
        url: Starting URL of the government wizard
        
    Returns:
        Dictionary with session_id, screenshot, current_url, html_context, message
    """
    start_time = time.time()
    config = get_config()
    
    log_tool_call('federalscout_start_discovery', {'url': url}, logger=logger)

    try:
        # Clean up expired sessions
        _cleanup_expired_sessions(config)

        # Generate session ID
        session_id = str(uuid.uuid4())

        # Create browser session
        session = BrowserSession(session_id, config)
        _active_sessions[session_id] = session

        logger.info(f"🆕 NEW SESSION: {session_id}")
        logger.info(f"   Total active sessions: {len(_active_sessions)}")
        logger.info(f"🌐 Navigating to: {url}")
        log_session_event(session_id, 'created', {'url': url}, logger=logger)
        session_logger = get_session_logger(session_id, logger)

        # Launch browser and create page
        await session.client.launch()
        await session.client.new_page()

        # Navigate to URL
        success, error = await session.client.navigate(url)
        if not success:
            return {
                'success': False,
                'error': error,
                'error_type': 'navigation_failed'
            }
        
        # Wait a moment for page to settle
        await asyncio.sleep(1)

        # Capture screenshot
        screenshot_b64, size, screenshot_file = await session.client.capture_screenshot()
        logger.info(f"📸 Screenshot: {screenshot_file} ({size} bytes)")

        # Extract HTML context
        html_context = await session.client.extract_html_context()
        
        # Get current URL
        current_url = await session.client.get_current_url()
        
        # Update session activity
        session.update_activity()
        
        # Build response
        result = {
            'success': True,
            'session_id': session_id,
            'screenshot': screenshot_b64,
            'current_url': current_url,
            'html_context': html_context,
            'message': (
                f"Discovery session started. Session ID: {session_id}\n"
                f"Current URL: {current_url}\n"
                f"Found {len(html_context.get('inputs', []))} inputs, "
                f"{len(html_context.get('buttons', []))} buttons.\n"
                f"Use federalscout_click_element or federalscout_get_page_info to continue."
            )
        }
        
        execution_time = (time.time() - start_time) * 1000
        log_tool_result('federalscout_start_discovery', True, execution_time, logger=logger)
        
        return result
        
    except Exception as e:
        error_msg = f"Failed to start discovery: {str(e)}"
        logger.error(error_msg, exc_info=True)
        
        execution_time = (time.time() - start_time) * 1000
        log_tool_result('federalscout_start_discovery', False, execution_time, error_msg, logger=logger)
        
        return {
            'success': False,
            'error': error_msg,
            'error_type': 'unexpected_error'
        }


# Tool 2: Click Element
async def federalscout_click_element(
    session_id: str,
    selector: str,
    selector_type: str = 'auto'
) -> Dict[str, Any]:
    """
    Click an element on the current page.
    
    Args:
        session_id: Session ID from start_discovery
        selector: CSS selector or text to click
        selector_type: Type of selector ('text', 'id', 'css', 'auto')
        
    Returns:
        Dictionary with success, screenshot, current_url, html_context
    """
    start_time = time.time()
    
    log_tool_call('federalscout_click_element', {
        'session_id': session_id,
        'selector': selector,
        'selector_type': selector_type
    }, logger=logger)

    try:
        # Get session
        session = _get_session(session_id)
        if not session:
            return {
                'success': False,
                'error': f"Session not found: {session_id}",
                'error_type': 'invalid_session'
            }

        session_logger = get_session_logger(session_id, logger)

        # Convert selector type string to enum
        try:
            sel_type = SelectorType(selector_type.lower())
        except ValueError:
            sel_type = SelectorType.AUTO

        # Log browser action
        logger.info(f"🖱️  Clicking element: '{selector}' (type: {selector_type})")

        # Click element
        success, error = await session.client.click_element(selector, sel_type)
        
        if not success:
            # Try to capture screenshot even if click failed
            try:
                screenshot_b64, _, screenshot_file = await session.client.capture_screenshot()
                logger.info(f"📸 Screenshot (error): {screenshot_file}")
            except:
                screenshot_b64 = None
            
            return {
                'success': False,
                'error': error,
                'error_type': 'click_failed',
                'screenshot': screenshot_b64,
                'suggestion': (
                    "Try using selector_type='id' for ID selectors, "
                    "or 'css' for CSS selectors. "
                    "For hidden elements, they will be clicked with JavaScript automatically."
                )
            }
        
        # Wait for navigation/changes
        await asyncio.sleep(1)
        try:
            await session.client.page.wait_for_load_state('networkidle', timeout=10000)
        except Exception as e:
            # Network idle timeout is not critical - page may still be usable
            logger.debug(f"Network idle timeout (non-critical): {e}")

        # Capture screenshot
        screenshot_b64, size, screenshot_file = await session.client.capture_screenshot()
        logger.info(f"📸 Screenshot: {screenshot_file} ({size} bytes)")

        # Extract HTML context
        html_context = await session.client.extract_html_context()
        
        # Get current URL
        current_url = await session.client.get_current_url()
        
        # Update session activity
        session.update_activity()
        
        result = {
            'success': True,
            'screenshot': screenshot_b64,
            'current_url': current_url,
            'html_context': html_context,
            'message': f"Clicked element: {selector}. Current URL: {current_url}"
        }
        
        execution_time = (time.time() - start_time) * 1000
        log_tool_result('federalscout_click_element', True, execution_time, logger=logger)
        
        return result
        
    except Exception as e:
        error_msg = f"Failed to click element: {str(e)}"
        logger.error(error_msg, exc_info=True)
        
        execution_time = (time.time() - start_time) * 1000
        log_tool_result('federalscout_click_element', False, execution_time, error_msg, logger=logger)
        
        return {
            'success': False,
            'error': error_msg,
            'error_type': 'unexpected_error'
        }


# Tool 3: Execute Diverse Actions (UNIVERSAL BATCH)
async def federalscout_execute_actions(
    session_id: str,
    actions: List[Dict[str, str]]
) -> Dict[str, Any]:
    """
    Execute multiple diverse actions in sequence (fill, click, etc.) with ONE screenshot at the end.
    This is the most powerful batch tool - it reduces conversation size dramatically by handling
    any combination of actions in one call.

    Args:
        session_id: Session ID from start_discovery
        actions: List of action dictionaries, each containing:
            - action: Action type ('fill', 'fill_enter', 'click', 'javascript_click', 'select')
            - selector: CSS selector or text for the element
            - value: Value to fill (required for fill/fill_enter/select, optional for click)
            - selector_type: How to find element (optional, defaults to 'auto', options: 'text', 'id', 'css', 'auto')

    Example - Mixed actions:
        actions = [
            {"action": "javascript_click", "selector": "#fsa_Input_MaritalStatusMarried"},
            {"action": "fill", "selector": "#fsa_Input_DateOfBirthMonth", "value": "05"},
            {"action": "fill", "selector": "#fsa_Input_DateOfBirthDay", "value": "15"},
            {"action": "fill_enter", "selector": "#fsa_Typeahead_StateOfResidence", "value": "Illinois"},
            {"action": "click", "selector": "Continue", "selector_type": "text"}
        ]

    Returns:
        Dictionary with success, screenshot (taken AFTER all actions), completed_count, failed_actions
    """
    start_time = time.time()

    log_tool_call('federalscout_execute_actions', {
        'session_id': session_id,
        'action_count': len(actions)
    }, logger=logger)

    try:
        # Get session
        session = _get_session(session_id)
        if not session:
            return {
                'success': False,
                'error': f"Session not found: {session_id}",
                'error_type': 'invalid_session'
            }

        completed_count = 0
        failed_actions = []

        logger.info(f"⚡ Batch executing {len(actions)} diverse actions")

        # Execute all actions sequentially
        for idx, action_dict in enumerate(actions, 1):
            action_type = action_dict.get('action', '').lower()
            selector = action_dict.get('selector')
            value = action_dict.get('value', '')
            selector_type = action_dict.get('selector_type', 'auto')

            if not action_type or not selector:
                failed_actions.append({
                    'index': idx,
                    'action': action_dict,
                    'error': 'Missing action type or selector'
                })
                continue

            # Log the action
            action_descriptions = {
                'fill': ('✍️', f"Filling '{selector}' = '{value}'"),
                'fill_enter': ('⌨️', f"Filling typeahead '{selector}' = '{value}'"),
                'click': ('🖱️', f"Clicking '{selector}'"),
                'javascript_click': ('🔘', f"JavaScript clicking '{selector}'"),
                'select': ('📋', f"Selecting '{selector}' = '{value}'")
            }
            emoji, description = action_descriptions.get(action_type, ('⚙️', f"Executing {action_type} on '{selector}'"))
            logger.info(f"  {idx}/{len(actions)} {emoji} {description}")

            success = False
            error = None

            # Execute based on action type
            try:
                if action_type in ['fill', 'fill_enter', 'select']:
                    # Field filling actions
                    interaction = InteractionType(action_type)
                    success, error = await session.client.fill_field(selector, value, interaction)

                elif action_type in ['click', 'javascript_click']:
                    # Click actions
                    sel_type = SelectorType(selector_type.lower())
                    use_javascript = (action_type == 'javascript_click')
                    success, error = await session.client.click_element(selector, sel_type, use_javascript)

                else:
                    error = f"Unknown action type: {action_type}"

            except Exception as e:
                error = str(e)

            if success:
                completed_count += 1
                # Small delay between actions
                await asyncio.sleep(0.3)
            else:
                failed_actions.append({
                    'index': idx,
                    'action': action_dict,
                    'error': error
                })
                logger.warning(f"  ❌ Failed action {idx}: {error}")

        # Wait for any page changes/navigation to settle
        try:
            await session.client.page.wait_for_load_state('networkidle', timeout=5000)
        except Exception:
            # Non-critical - page may still be usable
            pass

        # Capture ONE screenshot after all actions complete
        screenshot_b64, size, screenshot_file = await session.client.capture_screenshot()
        logger.info(f"📸 Screenshot (after batch): {screenshot_file} ({size} bytes)")

        # Update session activity
        session.update_activity()

        result = {
            'success': True,
            'screenshot': screenshot_b64,
            'completed_count': completed_count,
            'total_actions': len(actions),
            'failed_actions': failed_actions,
            'message': (
                f"Batch executed {completed_count}/{len(actions)} actions successfully. "
                f"{'No failures.' if not failed_actions else f'{len(failed_actions)} failed.'}"
            )
        }

        execution_time = (time.time() - start_time) * 1000
        log_tool_result('federalscout_execute_actions', True, execution_time, logger=logger)

        return result

    except Exception as e:
        error_msg = f"Failed to batch execute actions: {str(e)}"
        logger.error(error_msg, exc_info=True)

        execution_time = (time.time() - start_time) * 1000
        log_tool_result('federalscout_execute_actions', False, execution_time, error_msg, logger=logger)

        return {
            'success': False,
            'error': error_msg,
            'error_type': 'unexpected_error'
        }


# Tool 4: Get Page Info
async def federalscout_get_page_info(session_id: str) -> Dict[str, Any]:
    """
    Get detailed information about the current page.
    
    Extracts all form elements, buttons, and page metadata.
    
    Args:
        session_id: Session ID from start_discovery
        
    Returns:
        Dictionary with screenshot, current_url, page_title, elements
    """
    start_time = time.time()
    
    log_tool_call('federalscout_get_page_info', {'session_id': session_id}, logger=logger)

    try:
        # Get session
        session = _get_session(session_id)
        if not session:
            return {
                'success': False,
                'error': f"Session not found: {session_id}",
                'error_type': 'invalid_session'
            }

        logger.info("📄 Extracting page information (inputs, buttons, selects, etc.)")

        # NOTE: NO screenshot captured here to reduce conversation size
        # Screenshots are already available from start_discovery, click_element, and fill_field
        # This tool is for getting element data only

        # Get current URL
        current_url = await session.client.get_current_url()

        # Get page title
        page_title = await session.client.get_page_title()

        # Extract detailed HTML context (filtered for discovery - excludes chat/feedback/etc.)
        elements = await session.client.extract_html_context(for_discovery=True)

        # Build complete element lists with full details for discovery
        # Extract all relevant properties for each element type
        inputs_data = []
        for inp in elements.get('inputs', []):
            inputs_data.append({
                'id': inp.get('id'),
                'name': inp.get('name'),
                'type': inp.get('type'),
                'visible': inp.get('visible', True)
            })

        buttons_data = []
        for btn in elements.get('buttons', []):
            buttons_data.append({
                'id': btn.get('id'),
                'name': btn.get('name'),
                'type': btn.get('type'),
                'visible': btn.get('visible', True)
            })

        selects_data = []
        for sel in elements.get('selects', []):
            selects_data.append({
                'id': sel.get('id'),
                'name': sel.get('name'),
                'options': sel.get('options', [])[:10],  # Limit options to first 10
                'visible': sel.get('visible', True)
            })

        textareas_data = []
        for txt in elements.get('textareas', []):
            textareas_data.append({
                'id': txt.get('id'),
                'name': txt.get('name'),
                'visible': txt.get('visible', True)
            })

        # Update session activity
        session.update_activity()

        result = {
            'success': True,
            'current_url': current_url,
            'page_title': page_title,
            'elements': {
                'inputs': inputs_data,
                'selects': selects_data,
                'textareas': textareas_data,
                'buttons': buttons_data
            },
            'summary': {
                'total_inputs': len(inputs_data),
                'total_selects': len(selects_data),
                'total_textareas': len(textareas_data),
                'total_buttons': len(buttons_data)
            },
            'message': (
                f"Page info extracted (NO screenshot to reduce conversation size).\n"
                f"Found {len(inputs_data)} inputs, {len(selects_data)} dropdowns, "
                f"{len(textareas_data)} textareas, {len(buttons_data)} buttons.\n"
                f"Use the element IDs to interact with fields. "
                f"Screenshots are available from start_discovery, click_element, and fill_field."
            )
        }
        
        execution_time = (time.time() - start_time) * 1000
        log_tool_result('federalscout_get_page_info', True, execution_time, logger=logger)
        
        return result
        
    except Exception as e:
        error_msg = f"Failed to get page info: {str(e)}"
        logger.error(error_msg, exc_info=True)
        
        execution_time = (time.time() - start_time) * 1000
        log_tool_result('federalscout_get_page_info', False, execution_time, error_msg, logger=logger)
        
        return {
            'success': False,
            'error': error_msg,
            'error_type': 'unexpected_error'
        }


# Tool 5: Save Page Metadata
async def federalscout_save_page_metadata(
    session_id: str,
    page_metadata: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Save discovered page metadata to the session.
    
    Args:
        session_id: Session ID from start_discovery
        page_metadata: Page structure metadata (fields, buttons, etc.)
        
    Returns:
        Dictionary with success, total_pages_discovered, message
    """
    start_time = time.time()
    
    log_tool_call('federalscout_save_page_metadata', {
        'session_id': session_id,
        'page_number': page_metadata.get('page_number')
    }, logger=logger)

    try:
        # Get session
        session = _get_session(session_id)
        if not session:
            return {
                'success': False,
                'error': f"Session not found: {session_id}",
                'error_type': 'invalid_session'
            }

        # Validate page metadata structure
        try:
            page_structure = PageStructure(**page_metadata)
        except Exception as e:
            return {
                'success': False,
                'error': f"Invalid page metadata: {str(e)}",
                'error_type': 'validation_error'
            }

        logger.info(f"💾 Saving Page {page_structure.page_number}: '{page_structure.page_title}' ({len(page_structure.fields)} fields)")

        # Add to session's discovered pages
        session.pages_discovered.append(page_structure)

        # INCREMENTAL SAVE: Write partial wizard JSON after each page
        # This prevents data loss if conversation crashes before completion
        config = get_config()
        partial_wizard_path = config.wizards_dir / f"_partial_{session_id}.json"

        try:
            import json
            from models import WizardStructure, StartAction

            # Build partial wizard structure with what we have so far
            partial_wizard = WizardStructure(
                wizard_id=f"partial-{session_id[:8]}",  # Temporary ID
                name="[IN PROGRESS]",  # Will be updated on completion
                url=await session.client.get_current_url(),
                discovered_at=datetime.utcnow(),
                discovery_version=config.discovery_version,
                total_pages=len(session.pages_discovered),  # Current count
                start_action=None,  # Will be set on completion
                pages=session.pages_discovered
            )

            # Save to partial file
            with open(partial_wizard_path, 'w') as f:
                json.dump(partial_wizard.model_dump(exclude_none=True), f, indent=2, default=str)

            logger.info(f"📄 Incremental save: {partial_wizard_path.name} ({len(session.pages_discovered)} pages)")

        except Exception as e:
            # Don't fail the whole operation if incremental save fails
            logger.warning(f"Incremental save failed (non-critical): {e}")

        # Update session activity
        session.update_activity()

        result = {
            'success': True,
            'total_pages_discovered': len(session.pages_discovered),
            'partial_file': str(partial_wizard_path.name) if partial_wizard_path.exists() else None,
            'message': (
                f"Page {page_structure.page_number} metadata saved. "
                f"Total pages discovered: {len(session.pages_discovered)}. "
                f"Partial wizard saved to {partial_wizard_path.name}"
            )
        }
        
        execution_time = (time.time() - start_time) * 1000
        log_tool_result('federalscout_save_page_metadata', True, execution_time, logger=logger)
        
        return result
        
    except Exception as e:
        error_msg = f"Failed to save page metadata: {str(e)}"
        logger.error(error_msg, exc_info=True)
        
        execution_time = (time.time() - start_time) * 1000
        log_tool_result('federalscout_save_page_metadata', False, execution_time, error_msg, logger=logger)
        
        return {
            'success': False,
            'error': error_msg,
            'error_type': 'unexpected_error'
        }


# Tool 6: Complete Discovery
async def federalscout_complete_discovery(
    session_id: str,
    wizard_name: str,
    wizard_id: str,
    start_action: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Complete discovery and save wizard structure to JSON file.

    This tool finalizes the discovery process by:
    1. Building the complete WizardStructure from all discovered pages
    2. Saving to a JSON file in the wizards directory
    3. Returning the complete wizard structure for the agent to display

    Args:
        session_id: Session ID from start_discovery
        wizard_name: Human-readable name for the wizard (e.g., "FSA Student Aid Estimator")
        wizard_id: Filename slug (lowercase, hyphens, e.g., "fsa-estimator")
        start_action: Optional start action metadata (button that starts the wizard)

    Returns:
        Dictionary with:
            - success (bool): Whether discovery completed successfully
            - wizard_id (str): Filename of saved wizard JSON
            - saved_to (str): Full path where wizard was saved
            - wizard_structure (dict): Complete wizard JSON structure (use this to create artifact!)
            - validation (dict): Validation results showing completeness

    Example Response:
        {
            "success": true,
            "wizard_id": "fsa-estimator.json",
            "saved_to": "/path/to/wizards/fsa-estimator.json",
            "wizard_structure": {
                "wizard_id": "fsa-estimator",
                "name": "FSA Student Aid Estimator",
                "total_pages": 7,
                "pages": [...]  # Complete structure with all fields
            },
            "validation": {"is_complete": true, "missing_fields": []}
        }

    Agent Instructions:
        After receiving the response, create a code artifact (application/json) containing
        the wizard_structure to provide a visual, interactive view of the discovered structure.
    """
    start_time = time.time()
    
    log_tool_call('federalscout_complete_discovery', {
        'session_id': session_id,
        'wizard_name': wizard_name,
        'wizard_id': wizard_id
    }, logger=logger)
    
    try:
        # Get session
        session = _get_session(session_id)
        if not session:
            return {
                'success': False,
                'error': f"Session not found: {session_id}",
                'error_type': 'invalid_session'
            }
        
        # Check if any pages were discovered
        if not session.pages_discovered:
            return {
                'success': False,
                'error': "No pages discovered. Use federalscout_save_page_metadata to save pages first.",
                'error_type': 'no_pages_discovered'
            }
        
        # Get configuration
        config = get_config()
        
        # Get starting URL from session
        start_url = await session.client.get_current_url()
        
        # Build start action if provided
        start_action_obj = None
        if start_action:
            start_action_obj = StartAction(**start_action)
        
        # Build wizard structure
        wizard_structure = WizardStructure(
            wizard_id=wizard_id,
            name=wizard_name,
            url=start_url,
            discovered_at=datetime.utcnow(),
            discovery_version=config.discovery_version,
            total_pages=len(session.pages_discovered),
            start_action=start_action_obj,
            pages=session.pages_discovered
        )

        # Validate completeness
        validation = wizard_structure.validate_completeness()

        # NEW: Validate against universal Wizard Structure Schema
        wizard_json = wizard_structure.model_dump(mode='json', exclude_none=True)
        try:
            import json
            from jsonschema import validate as json_schema_validate, Draft7Validator
            from pathlib import Path

            # Load universal schema
            project_root = Path(__file__).parent.parent.parent.parent
            schema_path = project_root / "schemas" / "wizard-structure-v1.schema.json"

            if schema_path.exists():
                with open(schema_path, 'r') as f:
                    universal_schema = json.load(f)

                # Validate wizard data against universal schema
                json_schema_validate(wizard_json, universal_schema)
                logger.info("✅ Wizard structure validates against universal schema")
            else:
                logger.warning(f"⚠️  Universal schema not found at: {schema_path}")

        except Exception as e:
            logger.error(f"❌ Schema validation failed: {str(e)}")
            return {
                'success': False,
                'error': f"Wizard structure does not conform to universal schema: {str(e)}",
                'error_type': 'schema_validation_error',
                'suggestion': 'Check that all required fields have proper field_ids and selectors'
            }

        # Save to final file in wizard-structures subdirectory
        wizard_structures_dir = config.wizards_dir / "wizard-structures"
        wizard_structures_dir.mkdir(parents=True, exist_ok=True)
        output_path = wizard_structure.to_json_file(wizard_structures_dir)

        # Remove partial file if it exists
        partial_wizard_path = config.wizards_dir / f"_partial_{session_id}.json"
        if partial_wizard_path.exists():
            try:
                partial_wizard_path.unlink()
                logger.info(f"🗑️  Removed partial file: {partial_wizard_path.name}")
            except Exception as e:
                logger.warning(f"Could not remove partial file: {e}")

        logger.info("━" * 80)
        logger.info(f"✅ DISCOVERY COMPLETE!")
        logger.info(f"   Wizard: '{wizard_name}'")
        logger.info(f"   Total Pages: {len(session.pages_discovered)}")
        logger.info(f"   Saved to: {output_path.name}")
        logger.info("━" * 80)

        log_session_event(session_id, 'completed', {
            'wizard_id': wizard_id,
            'total_pages': len(session.pages_discovered),
            'output_path': str(output_path)
        }, logger=logger)

        # Close browser and clean up session
        await session.close()
        _active_sessions.pop(session_id, None)
        logger.info(f"🔒 SESSION CLOSED: {session_id}")
        logger.info(f"   Remaining active sessions: {len(_active_sessions)}")
        
        # Convert wizard structure to dict using mode='json' to handle datetime serialization
        # This ensures all datetime objects are converted to ISO format strings
        wizard_dict = wizard_structure.model_dump(mode='json', exclude_none=True)

        result = {
            'success': True,
            'wizard_id': f"{wizard_id}.json",
            'saved_to': str(output_path),
            'wizard_structure': wizard_dict,
            'validation': validation
        }
        
        execution_time = (time.time() - start_time) * 1000
        log_tool_result('federalscout_complete_discovery', True, execution_time, logger=logger)
        
        return result
        
    except Exception as e:
        error_msg = f"Failed to complete discovery: {str(e)}"
        logger.error(error_msg, exc_info=True)

        execution_time = (time.time() - start_time) * 1000
        log_tool_result('federalscout_complete_discovery', False, execution_time, error_msg, logger=logger)

        # Check if partial file exists - it may have all the discovered pages
        config = get_config()
        partial_wizard_path = config.wizards_dir / f"_partial_{session_id}.json"
        partial_file_info = None
        if partial_wizard_path.exists():
            partial_file_info = str(partial_wizard_path)
            logger.warning(f"⚠️  Partial wizard file preserved: {partial_wizard_path.name}")

        return {
            'success': False,
            'error': error_msg,
            'error_type': 'unexpected_error',
            'partial_file': partial_file_info,
            'recovery_note': (
                f"All discovered pages are saved in {partial_wizard_path.name}. "
                "You can manually rename this file to recover your work."
            ) if partial_file_info else None
        }


# Tool 7: Save User Data Schema
async def federalscout_save_schema(
    wizard_id: str,
    schema_content: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Save Claude-generated User Data Schema for a wizard.

    This tool saves the JSON Schema that defines the contract between FederalScout
    and FederalRunner. The schema defines what user data is required to execute the wizard.

    The schema is saved to: wizards/data-schemas/{wizard_id}-schema.json

    Args:
        wizard_id: The wizard identifier (must match a discovered wizard)
        schema_content: Complete JSON Schema object (must be valid draft-07 schema)

    Returns:
        Dictionary with:
            - success (bool): Whether schema was saved successfully
            - schema_path (str): Path where schema was saved
            - validation (dict): Schema validation results

    Example schema_content:
        {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "title": "FSA Student Aid Estimator - User Data",
            "type": "object",
            "required": ["birth_year", "marital_status", "state"],
            "properties": {
                "birth_year": {
                    "type": "string",
                    "description": "Year of birth (4 digits)",
                    "pattern": "^[0-9]{4}$"
                },
                "marital_status": {
                    "type": "string",
                    "enum": ["married", "unmarried"],
                    "description": "Marital status"
                }
            }
        }
    """
    start_time = time.time()

    log_tool_call('federalscout_save_schema', {
        'wizard_id': wizard_id
    }, logger=logger)

    try:
        # Get configuration
        config = get_config()

        # Validate schema_content is a valid JSON Schema (draft-07)
        try:
            from jsonschema import Draft7Validator

            # Check schema is valid
            Draft7Validator.check_schema(schema_content)
            logger.info("✅ Schema is valid JSON Schema (draft-07)")

        except Exception as e:
            return {
                'success': False,
                'error': f"Invalid JSON Schema: {str(e)}",
                'error_type': 'invalid_schema',
                'suggestion': 'Ensure schema follows JSON Schema draft-07 specification'
            }

        # Check required schema fields
        required_fields = ['$schema', 'type', 'properties']
        missing_fields = [f for f in required_fields if f not in schema_content]

        if missing_fields:
            return {
                'success': False,
                'error': f"Schema missing required fields: {', '.join(missing_fields)}",
                'error_type': 'incomplete_schema',
                'suggestion': 'Schema must have $schema, type, and properties fields'
            }

        # Verify corresponding wizard exists
        wizard_path = config.wizards_dir / "structure-schemas" / f"{wizard_id}.json"
        if not wizard_path.exists():
            logger.warning(f"⚠️  Wizard structure file not found: {wizard_path.name} (saving schema anyway)")

        # Create data-schemas directory if it doesn't exist
        schema_dir = config.wizards_dir / "data-schemas"
        schema_dir.mkdir(exist_ok=True)

        # Save schema to file
        schema_path = schema_dir / f"{wizard_id}-schema.json"

        import json
        with open(schema_path, 'w') as f:
            json.dump(schema_content, f, indent=2)

        logger.info("━" * 80)
        logger.info(f"✅ USER DATA SCHEMA SAVED!")
        logger.info(f"   Wizard: {wizard_id}")
        logger.info(f"   Properties: {len(schema_content.get('properties', {}))}")
        logger.info(f"   Required: {len(schema_content.get('required', []))}")
        logger.info(f"   Saved to: {schema_path.name}")
        logger.info("━" * 80)

        result = {
            'success': True,
            'schema_path': str(schema_path),
            'wizard_id': wizard_id,
            'validation': {
                'is_valid': True,
                'property_count': len(schema_content.get('properties', {})),
                'required_count': len(schema_content.get('required', []))
            },
            'message': (
                f"User Data Schema saved to {schema_path.name}. "
                f"This schema defines the contract for executing {wizard_id}."
            )
        }

        execution_time = (time.time() - start_time) * 1000
        log_tool_result('federalscout_save_schema', True, execution_time, logger=logger)

        return result

    except Exception as e:
        error_msg = f"Failed to save schema: {str(e)}"
        logger.error(error_msg, exc_info=True)

        execution_time = (time.time() - start_time) * 1000
        log_tool_result('federalscout_save_schema', False, execution_time, error_msg, logger=logger)

        return {
            'success': False,
            'error': error_msg,
            'error_type': 'unexpected_error'
        }


# Export all tool functions
__all__ = [
    'federalscout_start_discovery',
    'federalscout_click_element',
    'federalscout_execute_actions',  # Universal batch action tool (click + fill + everything)
    'federalscout_get_page_info',
    'federalscout_save_page_metadata',
    'federalscout_complete_discovery',
    'federalscout_save_schema'
]
