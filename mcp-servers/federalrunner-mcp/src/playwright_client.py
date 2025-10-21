"""
Playwright client for atomic wizard execution.

This module implements the execution engine that takes pre-mapped field values
(selector -> value) and executes wizards atomically with Playwright.

Key Design:
- Receives field_values dict with SELECTORS as keys (not field_ids)
- Mapping from field_id -> selector happens in execution_tools.py
- Each execution is atomic: launch -> fill all pages -> extract -> close
- Supports both Chromium (non-headless, debugging) and WebKit (headless, production)

Critical Patterns from FederalScout Discovery:
- javascript_click for hidden radio buttons (FSA pattern)
- fill_enter for typeahead fields (fill + Enter key)
- Intelligent wait times for dynamic content
"""

from pathlib import Path
from typing import Dict, List, Optional, Any
from playwright.async_api import async_playwright, Page, Browser, BrowserContext, Playwright
import base64
import logging
import time
import asyncio

from .models import (
    WizardStructure,
    PageStructure,
    FieldStructure,
    InteractionType,
    FieldType,
    SelectorType,
    StartAction,
    ContinueButton
)
from .config import FederalRunnerConfig

logger = logging.getLogger(__name__)


class PlaywrightClient:
    """
    Atomic wizard execution client.

    Each execution is self-contained and stateless:
    1. Launch browser
    2. Navigate and fill all pages
    3. Extract results
    4. Close browser

    No persistent sessions - designed for Cloud Run stateless execution.
    """

    def __init__(self, config: FederalRunnerConfig):
        """
        Initialize Playwright client with configuration.

        Args:
            config: FederalRunnerConfig with browser and execution settings
        """
        self.config = config
        self.playwright: Optional[Playwright] = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None

    async def execute_wizard_atomically(
        self,
        wizard_structure: WizardStructure,
        field_values: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute wizard atomically with pre-mapped field values.

        CRITICAL: field_values keys are SELECTORS (not field_ids).
        The mapping from field_id -> selector happens in execution_tools.py.

        Args:
            wizard_structure: Loaded wizard structure (from wizard-structures/)
            field_values: Dict mapping selector -> value
                         e.g., {"#fsa_Input_DateOfBirthMonth": "05"}

        Returns:
            {
                'success': True,
                'wizard_id': 'fsa-estimator',
                'results': {...extracted results...},
                'screenshots': [base64...],
                'pages_completed': 7,
                'execution_time_ms': 8500
            }
        """
        start_time = time.time()
        screenshots = []
        pages_completed = 0

        try:
            logger.info("=" * 70)
            logger.info(f" Starting atomic execution: {wizard_structure.wizard_id}")
            logger.info(f"   URL: {wizard_structure.url}")
            logger.info(f"   Total pages: {wizard_structure.total_pages}")
            logger.info("=" * 70)

            # 1. Launch browser
            await self._launch_browser()

            # 2. Navigate to wizard URL with retry logic
            # FSA normally loads in 9-20s when working, but is non-deterministic
            # Strategy: Short timeout (20s) × multiple retries (5 attempts) = better UX than long timeout
            logger.info(f" Navigating to: {wizard_structure.url}")
            max_retries = 4  # 5 total attempts (initial + 4 retries)
            retry_delay = 2000  # 2 seconds between retries
            navigation_timeout_per_attempt = 20000  # 20 seconds per attempt

            for attempt in range(max_retries + 1):
                try:
                    if attempt > 0:
                        logger.warning(f"   Retry attempt {attempt}/{max_retries} after {retry_delay/1000}s delay...")
                        await self.page.wait_for_timeout(retry_delay)

                    await self.page.goto(
                        wizard_structure.url,
                        wait_until='networkidle',
                        timeout=navigation_timeout_per_attempt  # 20s per attempt
                    )
                    logger.info(f"   Navigation successful (attempt {attempt + 1}/{max_retries + 1})")
                    break  # Success - exit retry loop

                except Exception as nav_error:
                    if attempt == max_retries:
                        # Final attempt failed - raise error
                        logger.error(f"   Navigation failed after {max_retries + 1} attempts")
                        raise nav_error
                    else:
                        # Will retry
                        logger.warning(f"   Navigation timeout on attempt {attempt + 1}/{max_retries + 1}, will retry...")
                        continue

            await self.page.wait_for_timeout(1000)  # Let page settle
            screenshots.append(await self._take_screenshot("initial_page"))

            # 3. Execute start action (if exists)
            if wizard_structure.start_action:
                logger.info(f"->  Executing start action: {wizard_structure.start_action.selector}")
                await self._execute_start_action(wizard_structure.start_action)
                await self.page.wait_for_load_state('networkidle')
                await self.page.wait_for_timeout(1000)
                screenshots.append(await self._take_screenshot("after_start_action"))

            # 4. Fill all pages sequentially
            for page_structure in wizard_structure.pages:
                logger.info(f"=-> Page {page_structure.page_number}/{wizard_structure.total_pages}: {page_structure.page_title}")

                # Fill all fields on this page
                for field in page_structure.fields:
                    # Look up value by selector (NOT field_id!)
                    field_value = field_values.get(field.selector)

                    # Check if required field is missing
                    if field_value is None and field.required:
                        logger.error(f"L Missing required field: {field.field_id} (selector: {field.selector})")
                        raise ValueError(
                            f"Missing required field: {field.field_id}. "
                            f"Selector: {field.selector}. "
                            f"Check that user_data includes this field_id."
                        )

                    # Fill field if value provided
                    if field_value is not None:
                        await self._fill_field(field, field_value)
                        await self.page.wait_for_timeout(300)  # Brief pause between fields

                # Take screenshot after filling page
                screenshot_label = f"page_{page_structure.page_number}_filled"
                screenshots.append(await self._take_screenshot(screenshot_label))

                # Click continue button to go to next page
                logger.info(f"->  Clicking continue button")
                await self._click_continue(page_structure.continue_button)
                await self.page.wait_for_load_state('networkidle')
                await self.page.wait_for_timeout(1500)  # Wait for next page to load

                pages_completed += 1

            # 5. Extract results from final page
            logger.info(f"=-> Extracting results from final page")
            final_screenshot = await self._take_screenshot("final_results")
            screenshots.append(final_screenshot)

            results = await self._extract_results()

            execution_time_ms = int((time.time() - start_time) * 1000)

            logger.info(f" Execution completed in {execution_time_ms}ms")

            # For production (headless mode), only include final screenshot to reduce response size
            # This prevents timeout issues with Claude.ai's MCP client
            response_screenshots = screenshots if not self.config.headless else [final_screenshot]

            return {
                'success': True,
                'wizard_id': wizard_structure.wizard_id,
                'results': results,
                'screenshots': response_screenshots,
                'pages_completed': pages_completed,
                'execution_time_ms': execution_time_ms,
                'timestamp': time.time()
            }

        except Exception as e:
            logger.error(f"L Execution failed: {type(e).__name__}: {e}")

            # Capture error screenshot if possible
            error_screenshot = None
            try:
                if self.page:
                    error_screenshot = await self._take_screenshot("error")
                    screenshots.append(error_screenshot)
            except Exception as screenshot_error:
                logger.warning(f"Could not capture error screenshot: {screenshot_error}")

            execution_time_ms = int((time.time() - start_time) * 1000)

            # For production (headless mode), only include the last screenshot to reduce response size
            # CRITICAL: Always include the error screenshot (where execution failed) for Visual Validation Loop
            # The error screenshot shows the error message and provides sufficient context for Claude Vision
            if self.config.headless and len(screenshots) > 0:
                # Keep only the last screenshot (error screenshot) - minimal payload, prevents timeouts
                response_screenshots = [screenshots[-1]]
            else:
                # Local dev: include all screenshots for complete debugging
                response_screenshots = screenshots

            return {
                'success': False,
                'error': str(e),
                'error_type': type(e).__name__,
                'screenshots': response_screenshots,
                'pages_completed': pages_completed,
                'execution_time_ms': execution_time_ms,
                'timestamp': time.time()
            }

        finally:
            # ALWAYS close browser (atomic execution requirement)
            await self._close_browser()

    async def _launch_browser(self):
        """
        Launch browser with configured settings.

        Browser selection:
        - Chromium: Local development (non-headless, visible)
        - WebKit: Production (headless, FSA-compatible)
        """
        self.playwright = await async_playwright().start()

        # Select browser type based on configuration
        if self.config.browser_type == "webkit":
            browser_launcher = self.playwright.webkit
            logger.info("< Using WebKit (FSA-compatible for headless)")
        elif self.config.browser_type == "firefox":
            browser_launcher = self.playwright.firefox
            logger.info(">-> Using Firefox")
        else:
            browser_launcher = self.playwright.chromium
            logger.info("=5 Using Chromium")

        # Launch browser
        self.browser = await browser_launcher.launch(
            headless=self.config.headless,
            slow_mo=self.config.slow_mo
        )

        # Create context with viewport settings
        self.context = await self.browser.new_context(
            viewport={
                'width': self.config.viewport_width,
                'height': self.config.viewport_height
            },
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )

        # Create page
        self.page = await self.context.new_page()

        logger.info(
            f" Browser launched: {self.config.browser_type} "
            f"(headless={self.config.headless}, viewport={self.config.viewport_width}x{self.config.viewport_height})"
        )

    async def _fill_field(self, field: FieldStructure, value: Any):
        """
        Fill a single field based on its interaction type.

        Implements critical patterns from FederalScout discovery:
        - javascript_click: For hidden radio buttons (FSA pattern)
        - fill_enter: For typeahead fields (fill + Enter key)
        - fill: For standard text/number inputs
        - select: For dropdown menus
        - group/array: Repeatable fields (e.g., adding loans)

        Args:
            field: FieldStructure with selector and interaction type
            value: Value to fill (type depends on field_type)
        """
        logger.debug(f"    Filling {field.field_id}: {field.selector} = {value}")

        # Special handling for array/group fields (repeatable fields)
        # If field_type is "group" and value is a list, this is a repeatable field
        if field.field_type == FieldType.GROUP and isinstance(value, list):
            if len(value) == 0:
                # Empty array means user doesn't want to add any items
                # Skip this field entirely (don't click anything)
                logger.debug(f"    -> Skipped group field (empty array - no items to add)")
                return
            else:
                # Repeatable field with items - add each one
                logger.debug(f"    -> Repeatable field: adding {len(value)} item(s)")

                # Each item in the list is a dict with values for sub_fields
                for index, item_data in enumerate(value):
                    logger.debug(f"       Adding item {index + 1}/{len(value)}")

                    # Click the "Add" button to show the form
                    add_button_selector = field.add_button_selector
                    if not add_button_selector:
                        raise ValueError(f"Repeatable field '{field.field_id}' is missing add_button_selector")

                    await self.page.click(add_button_selector)
                    await self.page.wait_for_timeout(500)  # Wait for form to appear

                    # Fill each sub-field with the corresponding value from item_data
                    for sub_field in field.sub_fields:
                        sub_field_value = item_data.get(sub_field.field_id)

                        if sub_field_value is None:
                            logger.warning(f"          Missing value for sub_field: {sub_field.field_id}")
                            continue

                        logger.debug(f"          Filling {sub_field.field_id}: {sub_field.selector} = {sub_field_value}")

                        # Fill sub-field based on its interaction type
                        if sub_field.interaction == InteractionType.FILL:
                            await self.page.fill(sub_field.selector, str(sub_field_value))
                        elif sub_field.interaction == InteractionType.SELECT:
                            # Use the same Unicode handling strategy as main SELECT
                            # OPTIMIZED: 5-second timeout per strategy (fast failure)
                            value_str = str(sub_field_value)
                            try:
                                await self.page.select_option(sub_field.selector, value_str, timeout=5000)
                            except Exception:
                                # Try Unicode apostrophe version
                                await self.page.select_option(sub_field.selector, value_str.replace("'", "\u2019"), timeout=5000)
                        else:
                            logger.warning(f"          Unsupported interaction type for sub_field: {sub_field.interaction}")

                    # Click "Save" button to save this item
                    # The save button is usually near the form, look for common patterns
                    # From the screenshots, it's a "Save" button next to the fields
                    try:
                        # Try finding by text "Save" (most reliable)
                        await self.page.get_by_text("Save", exact=True).click()
                        await self.page.wait_for_timeout(500)  # Wait for item to be added to table
                        logger.debug(f"          Item {index + 1} saved")
                    except Exception as e:
                        logger.error(f"          Failed to click Save button: {e}")
                        raise ValueError(f"Could not save item {index + 1} for field '{field.field_id}'")

                logger.debug(f"    -> Completed adding {len(value)} item(s) to {field.field_id}")
                return

        try:
            if field.interaction == InteractionType.FILL:
                # Standard text/number input
                await self.page.fill(field.selector, str(value))
                logger.debug(f"    -> Filled with standard fill()")

            elif field.interaction == InteractionType.FILL_ENTER:
                # Typeahead: fill then press Enter
                await self.page.fill(field.selector, str(value))
                await self.page.press(field.selector, 'Enter')
                await self.page.wait_for_timeout(500)  # Let dropdown close
                logger.debug(f"    -> Filled with fill_enter (typeahead)")

            elif field.interaction == InteractionType.CLICK:
                # Standard click
                await self.page.click(field.selector)
                logger.debug(f"    -> Clicked with standard click()")

            elif field.interaction == InteractionType.JAVASCRIPT_CLICK:
                # JavaScript click for hidden elements (FSA radio buttons)
                await self.page.evaluate(f"document.querySelector('{field.selector}').click()")
                logger.debug(f"    -> Clicked with JavaScript (hidden element)")

            elif field.interaction == InteractionType.SELECT:
                # Dropdown select with Unicode apostrophe handling
                # FSA dropdowns use Unicode right single quotation mark (\u2019) instead of ASCII apostrophe (')
                # Strategy: Try multiple variations to handle Unicode mismatches
                # OPTIMIZED: Use 5-second timeout per strategy (instead of default 30s)
                # This makes Unicode fallback fast: 5s fail + immediate success = ~6s total

                value_str = str(value)
                selection_successful = False
                last_error = None

                # Timeout per strategy (5 seconds instead of default 30 seconds)
                # Worst case: 4 strategies × 5s = 20s (vs 120s with default timeout)
                # Best case with Unicode: ~6s (first fails at 5s, second succeeds immediately)
                STRATEGY_TIMEOUT_MS = 5000

                # Try 4 strategies in order:
                # 1. Original value (ASCII apostrophe if user provided it)
                # 2. Unicode apostrophe version (replace ' with \u2019)
                # 3. Label matching (use label= parameter)
                # 4. Label matching with Unicode
                # Each strategy has format: (name, value_arg, label_arg)

                strategies = [
                    ("original value", value_str, None),
                    ("unicode apostrophe", value_str.replace("'", "\u2019"), None),
                    ("label (original)", None, value_str),
                    ("label (unicode)", None, value_str.replace("'", "\u2019"))
                ]

                for strategy_name, value_arg, label_arg in strategies:
                    try:
                        if label_arg is not None:
                            # Label-based selection
                            await self.page.select_option(
                                field.selector,
                                label=label_arg,
                                timeout=STRATEGY_TIMEOUT_MS
                            )
                        else:
                            # Value-based selection
                            await self.page.select_option(
                                field.selector,
                                value_arg,
                                timeout=STRATEGY_TIMEOUT_MS
                            )
                        selection_successful = True
                        logger.debug(f"    -> Selected dropdown option using strategy: {strategy_name}")
                        break
                    except Exception as e:
                        last_error = e
                        logger.debug(f"    -> Strategy '{strategy_name}' failed: {str(e)[:100]}")
                        continue

                if not selection_successful:
                    # All strategies failed - raise the last error
                    raise last_error

            else:
                logger.warning(f"    ->  Unknown interaction type: {field.interaction}")

        except Exception as e:
            logger.error(f"    L Failed to fill field {field.field_id}: {e}")
            raise ValueError(
                f"Failed to fill field '{field.field_id}' (selector: {field.selector}). "
                f"Error: {e}. "
                f"Field may not be visible or selector may be incorrect."
            )

    async def _click_continue(self, continue_button: ContinueButton):
        """
        Click the continue/next button to advance to next page.

        Args:
            continue_button: ContinueButton with selector and type
        """
        logger.debug(f"  =->  Clicking continue: {continue_button.selector}")

        try:
            if continue_button.selector_type == SelectorType.TEXT:
                # Click by text content
                await self.page.get_by_text(continue_button.selector, exact=True).click()
            elif continue_button.selector_type == SelectorType.ID:
                # Click by ID selector - ensure it has # prefix
                selector = continue_button.selector
                if not selector.startswith('#'):
                    selector = f'#{selector}'
                await self.page.click(selector)
            else:
                # Click by CSS selector (default)
                await self.page.click(continue_button.selector)

        except Exception as e:
            logger.error(f"    L Failed to click continue button: {e}")
            raise ValueError(
                f"Failed to click continue button (selector: {continue_button.selector}). "
                f"Button may not be visible or selector may be incorrect."
            )

    async def _take_screenshot(self, label: str = "screenshot") -> str:
        """
        Take optimized screenshot and return base64-encoded string.

        Optimization strategy:
        - JPEG format (smaller than PNG)
        - Quality 80 (good balance)
        - Viewport only (not full page)
        - Target: ~50-100KB per screenshot

        Args:
            label: Label for logging purposes

        Returns:
            Base64-encoded JPEG screenshot
        """
        try:
            screenshot_bytes = await self.page.screenshot(
                type='jpeg',
                quality=self.config.screenshot_quality,
                full_page=False  # Viewport only (faster, smaller)
            )

            screenshot_b64 = base64.b64encode(screenshot_bytes).decode('utf-8')
            size_kb = len(screenshot_bytes) / 1024

            # Save to disk if configured (for local testing/debugging)
            if self.config.save_screenshots:
                from datetime import datetime
                timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")[:-3]
                filename = f"screenshot_{timestamp}_{label}.jpg"
                screenshot_path = self.config.screenshot_dir / filename

                # Ensure directory exists
                screenshot_path.parent.mkdir(parents=True, exist_ok=True)

                with open(screenshot_path, 'wb') as f:
                    f.write(screenshot_bytes)

                logger.debug(f"  ->  Screenshot saved: {screenshot_path.name}")

            logger.debug(f"  =-> Screenshot captured: {label} ({size_kb:.1f}KB)")

            return screenshot_b64

        except Exception as e:
            logger.warning(f"  ->  Screenshot failed for {label}: {e}")
            return ""  # Return empty string on failure

    async def _extract_results(self) -> Dict[str, Any]:
        """
        Extract results from the final page.

        TODO: Make this wizard-specific (FSA vs SSA vs IRS).
        For now, extract all visible text content.

        Future enhancement:
        - Load wizard-specific extraction rules
        - Parse structured data (tables, key-value pairs)
        - Extract specific fields based on wizard type

        Returns:
            Dict with extracted results
        """
        try:
            # Get page URL (helps identify which page we're on)
            page_url = self.page.url

            # Get page title
            page_title = await self.page.title()

            # Get main content text (body)
            body_text = await self.page.inner_text('body')

            # Try to find specific result sections (common patterns)
            results = {
                'page_url': page_url,
                'page_title': page_title,
                'body_text': body_text[:2000],  # Limit to first 2000 chars
                'note': 'Result extraction is currently generic. Wizard-specific parsing will be implemented per wizard type.'
            }

            # TODO: Add wizard-specific extraction logic
            # if wizard_id == 'fsa-estimator':
            #     results['student_aid_index'] = extract_sai(page)
            #     results['pell_grant_estimate'] = extract_pell(page)

            logger.info(f"   Results extracted from: {page_url}")

            return results

        except Exception as e:
            logger.error(f"  L Result extraction failed: {e}")
            return {
                'error': 'Failed to extract results',
                'error_details': str(e)
            }

    async def _execute_start_action(self, start_action: StartAction):
        """
        Execute the start action to begin wizard.

        Args:
            start_action: StartAction with selector and type
        """
        logger.debug(f"  ->  Start action: {start_action.selector}")

        try:
            if start_action.selector_type == SelectorType.TEXT:
                # Click by text content
                await self.page.get_by_text(start_action.selector, exact=True).click()
            elif start_action.selector_type == SelectorType.ID:
                # Click by ID selector - ensure it has # prefix
                selector = start_action.selector
                if not selector.startswith('#'):
                    selector = f'#{selector}'
                await self.page.click(selector)
            else:
                # Click by CSS selector (default)
                await self.page.click(start_action.selector)

        except Exception as e:
            logger.error(f"    L Failed to execute start action: {e}")
            raise ValueError(
                f"Failed to execute start action (selector: {start_action.selector}). "
                f"Start button may not be visible or selector may be incorrect."
            )

    async def _close_browser(self):
        """
        Close browser and clean up resources.

        CRITICAL: Always called in finally block to ensure cleanup.
        """
        try:
            if self.browser:
                await self.browser.close()
                logger.info("=K Browser closed")

            if self.playwright:
                await self.playwright.stop()

        except Exception as e:
            logger.warning(f"Error closing browser: {e}")

        finally:
            self.browser = None
            self.context = None
            self.page = None
            self.playwright = None
