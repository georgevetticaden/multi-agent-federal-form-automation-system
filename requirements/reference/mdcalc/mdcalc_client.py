#!/usr/bin/env python3
"""
MDCalc Automation Client - Universal calculator support through visual understanding.

Provides browser automation for all 825 MDCalc medical calculators using a screenshot-based
approach that enables Claude to visually understand and interact with any calculator interface.

Key Innovation:
    Instead of maintaining 825 different selector configurations, this client captures
    screenshots that Claude analyzes visually to understand available fields and options.

Core Features:
    - Universal calculator support without hardcoded selectors
    - Intelligent zoom adjustment for long calculator forms
    - Automatic removal of sticky overlays that obscure fields
    - Optimized screenshot compression (~23KB per image)
    - Semantic search across all MDCalc calculators
"""

import asyncio
from playwright.async_api import async_playwright
import json
import os
from pathlib import Path
from typing import Dict, List, Optional
import logging
import base64
import re

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MDCalcClient:
    """
    MDCalc automation client using Playwright for browser control.

    Implements screenshot-based universal calculator support for all 825 MDCalc calculators.
    Instead of maintaining complex selectors, Claude visually understands calculators through screenshots.

    Key Features:
    - Universal Support: One approach works for all calculators
    - Visual Understanding: Screenshots enable Claude to see and understand any calculator
    - Smart Zoom: Automatically adjusts viewport to capture long calculators
    - Overlay Handling: Removes sticky Results sections that obscure fields
    - Tab Management: Keeps calculator tabs open for user review (creates new tabs for each action)

    Main Methods:
        get_all_calculators(): Load compact catalog of all 825 calculators
        search_calculators(): Use MDCalc's semantic search
        get_calculator_details(): Capture screenshot for visual understanding
        execute_calculator(): Execute calculator with mapped values
    """

    def __init__(self):
        self.base_url = "https://www.mdcalc.com"
        self.playwright = None
        self.browser = None
        self.context = None

    def load_auth_state(self):
        """
        Load authentication state from multiple possible locations.

        Priority order:
        1. Cloud Run: Secret Manager mounted at /app/auth/mdcalc_auth_state.json
        2. Local dev: recordings/auth/mdcalc_auth_state.json
        3. None: Proceed without authentication (may fail on MDCalc)
        """
        # Try Cloud Run secret mount first (production)
        cloud_run_auth_path = Path("/app/auth/mdcalc_auth_state.json")
        if cloud_run_auth_path.exists():
            logger.info(f"✅ Loading auth state from Cloud Run secret: {cloud_run_auth_path}")
            return str(cloud_run_auth_path)

        # Fall back to local development path
        local_auth_path = Path(__file__).parent.parent.parent.parent / "recordings" / "auth" / "mdcalc_auth_state.json"
        if local_auth_path.exists():
            logger.info(f"✅ Loading auth state from local: {local_auth_path}")
            return str(local_auth_path)

        logger.warning("⚠️  No auth state found - MDCalc may block headless browsers")
        logger.warning("   To fix: Run tools/recording-generator/manual_login.py and upload to Secret Manager")
        return None

    async def initialize(self, headless=True, use_auth=True):
        """
        Initialize Playwright browser instance.

        Args:
            headless (bool): Run browser in headless mode (default: True).
                            Set to False to see browser during demos.
                            Controlled by MDCALC_HEADLESS env var in MCP config.
            use_auth (bool): Load authentication state if available.

        Demo Mode:
            When headless=False and Chrome is running with --remote-debugging-port=9222,
            connects to the existing browser instead of launching a new one.
            This allows using a pre-positioned browser window for demos.
        """
        # Store headless mode for potential reconnection
        self.headless_mode = headless

        self.playwright = await async_playwright().start()

        # Check if we should connect to existing browser (demo mode)
        use_existing_browser = False
        if not headless:
            # Try to connect to existing Chrome instance on port 9222
            try:
                import socket
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                result = sock.connect_ex(('localhost', 9222))
                sock.close()
                use_existing_browser = (result == 0)
                if use_existing_browser:
                    logger.info("Demo mode: Connecting to existing Chrome browser on port 9222")
            except:
                pass

        if use_existing_browser:
            # Connect to existing browser instance
            try:
                self.browser = await self.playwright.chromium.connect_over_cdp(
                    endpoint_url="http://localhost:9222",
                    timeout=5000
                )
                logger.info("Successfully connected to existing Chrome browser")
            except Exception as e:
                logger.warning(f"Failed to connect to existing browser: {e}")
                logger.info("Falling back to launching new browser")
                # Fallback to launching new browser
                self.browser = await self.playwright.chromium.launch(
                    headless=False,
                    args=['--disable-blink-features=AutomationControlled']
                )
        else:
            # Launch new browser (normal mode)
            # Use Chrome channel in headless mode for better compatibility with MDCalc
            if headless:
                try:
                    self.browser = await self.playwright.chromium.launch(
                        headless=True,
                        channel="chrome",  # Use real Chrome instead of Chromium
                        args=[
                            '--disable-blink-features=AutomationControlled',
                            '--disable-gpu',  # Disable GPU to avoid screenshot issues in headless
                            '--disable-dev-shm-usage',  # Overcome limited resource problems
                            '--no-sandbox',  # Required for Cloud Run
                        ]
                    )
                    logger.info("Launched Chrome in headless mode")
                except Exception as e:
                    logger.warning(f"Chrome not available, falling back to Chromium: {e}")
                    self.browser = await self.playwright.chromium.launch(
                        headless=True,
                        args=[
                            '--disable-blink-features=AutomationControlled',
                            '--disable-gpu',  # Disable GPU to avoid screenshot issues in headless
                            '--disable-dev-shm-usage',  # Overcome limited resource problems
                            '--no-sandbox',  # Required for Cloud Run
                        ]
                    )
            else:
                self.browser = await self.playwright.chromium.launch(
                    headless=False,
                    args=['--disable-blink-features=AutomationControlled']
                )

        # For demo mode with existing browser, try to reuse existing context
        if use_existing_browser:
            # Get existing contexts
            contexts = self.browser.contexts
            if contexts:
                # Reuse first available context
                self.context = contexts[0]
                logger.info(f"Demo mode: Reusing existing browser context with {len(self.context.pages)} open tabs")
            else:
                # Create new context in existing browser
                self.context = await self.browser.new_context(
                    viewport={'width': 1920, 'height': 1080},
                    user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Chrome/120.0.0.0 Safari/537.36'
                )
                logger.info("Demo mode: Created new context in existing browser")
        else:
            # Normal mode - create new context
            context_params = {
                'viewport': {'width': 1920, 'height': 1080},
                'user_agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Chrome/120.0.0.0 Safari/537.36'
            }

            if use_auth:
                auth_state_path = self.load_auth_state()
                if auth_state_path:
                    context_params['storage_state'] = auth_state_path

            self.context = await self.browser.new_context(**context_params)
            logger.info("Browser initialized successfully")

    async def get_all_calculators(self) -> List[Dict]:
        """
        Load the complete MDCalc calculator catalog optimized for LLM processing.

        Returns a compact format to minimize token usage while preserving
        all essential information for calculator selection.

        Returns:
            List[Dict]: List of 825 calculators, each containing:
                - id (str): Calculator ID (e.g., "1752")
                - name (str): Calculator name (e.g., "HEART Score")
                - category (str): Medical category (e.g., "Cardiology")

        Note:
            URLs are omitted but can be constructed as:
            https://www.mdcalc.com/calc/{id}
        """
        logger.info("get_all_calculators called - starting catalog load")

        # Load from scraped catalog file
        catalog_path = Path(__file__).parent / "calculator-catalog" / "mdcalc_catalog.json"

        logger.info(f"Looking for catalog at: {catalog_path}")
        logger.info(f"Catalog path exists: {catalog_path.exists()}")
        logger.info(f"Parent directory: {catalog_path.parent}")
        logger.info(f"Parent exists: {catalog_path.parent.exists()}")

        # List what's actually in the parent directory
        try:
            if catalog_path.parent.exists():
                files = list(catalog_path.parent.iterdir())
                logger.info(f"Files in {catalog_path.parent}: {[f.name for f in files]}")
            else:
                logger.error(f"Parent directory does not exist: {catalog_path.parent}")
        except Exception as e:
            logger.error(f"Error listing parent directory: {e}")

        if not catalog_path.exists():
            logger.error(f"Catalog file not found at {catalog_path}")
            raise FileNotFoundError(
                f"Calculator catalog not found at {catalog_path}. "
                f"Please run: python tools/calculator-scraper/scrape_mdcalc.py"
            )

        try:
            with open(catalog_path, 'r') as f:
                catalog = json.load(f)
                logger.info(f"Loaded {catalog['total_count']} calculators from catalog")

                # Return optimized format - just id, name, and category
                optimized = []
                for calc in catalog['calculators']:
                    # Truncate very long names to save tokens
                    name = calc.get('name', '')
                    if len(name) > 100:
                        name = name[:97] + '...'

                    optimized.append({
                        'id': calc.get('id'),
                        'name': name,
                        'category': calc.get('category', 'General')
                    })

                return optimized
        except Exception as e:
            raise RuntimeError(f"Failed to load calculator catalog: {e}")

    async def search_calculators(self, query: str, limit: int = 10) -> List[Dict]:
        """
        Search for calculators using MDCalc's web search.

        Uses MDCalc's sophisticated search algorithm that understands
        clinical relationships and semantic matches.

        Args:
            query (str): Search term (e.g., "chest pain", "HEART", "pneumonia")
            limit (int): Maximum results to return (default: 10)

        Returns:
            List[Dict]: Matching calculators, each containing:
                - id (str): Calculator ID
                - title (str): Calculator name
                - slug (str): URL slug
                - url (str): Full MDCalc URL
                - description (str): Brief description (if available)
        """
        # Use MDCalc's web search directly for better semantic matching
        page = await self.context.new_page()

        try:
            # First go to MDCalc homepage
            logger.info(f"Navigating to MDCalc...")
            await page.goto(self.base_url, wait_until='networkidle')
            await page.wait_for_timeout(2000)

            # Find and use the search box
            search_input = await page.wait_for_selector('input[type="search"], input[placeholder*="Search"]', timeout=5000)

            logger.info(f"Searching for: {query}")
            await search_input.fill(query)
            await search_input.press('Enter')

            # Wait for navigation and results to load
            await page.wait_for_load_state('networkidle')
            await page.wait_for_timeout(3000)

            # Look for actual search result containers
            # Based on debug output, results are in calculatorRow_row-container__HM_dC elements
            calculators = await page.evaluate(f'''
                () => {{
                    const limit = {limit};

                    // Check if we're actually on a search results page
                    // MDCalc shows "No tool found for..." when there are no results
                    // Look for the specific div with class containing "search-results-message"
                    const noToolFound = document.querySelector('.search_search-results-message__nK_GX, [class*="search-results-message"]');
                    if (noToolFound && noToolFound.textContent.includes('No tool')) {{
                        // No search results found
                        return [];
                    }}

                    // Look for search result rows - these have the specific class
                    const resultRows = document.querySelectorAll('.calculatorRow_row-container__HM_dC');

                    if (resultRows.length === 0) {{
                        // No results found - return empty array
                        return [];
                    }}

                    // Process the result rows
                    return Array.from(resultRows).slice(0, limit).map(row => {{
                        const link = row.querySelector('a[href*="/calc/"]');
                        if (!link) return null;

                        const href = link.href;
                        const idMatch = href.match(/calc\\/(\\d+)/);
                        const slugMatch = href.match(/calc\\/\\d+\\/([^/]+)/);

                        // Get title from the specific title div
                        const titleElement = row.querySelector('.calculatorRow_row-title__8tXMs') || link;
                        const descElement = row.querySelector('.calculatorRow_row-bottom__eA_gR');

                        return {{
                            title: titleElement.textContent.trim(),
                            description: descElement ? descElement.textContent.trim() : '',
                            url: href,
                            id: idMatch ? idMatch[1] : null,
                            slug: slugMatch ? slugMatch[1] : null
                        }};
                    }}).filter(item => item && item.url);
                }}
            ''')

            logger.info(f"Found {len(calculators)} calculators for '{query}'")
            return calculators

        finally:
            # Keep page open for user to review while looking at field inventory/mappings
            # await page.close()
            pass

    async def ensure_browser_connected(self):
        """Ensure browser and context are connected and ready."""
        try:
            # Check if we have a context at all
            if not self.context or not self.browser:
                logger.info("No browser context found, initializing...")
                await self.initialize(headless=self.headless_mode if hasattr(self, 'headless_mode') else True)
                return

            # Try to use the context to verify it's still valid
            try:
                # This will throw if context is closed
                _ = self.context.pages
            except Exception:
                # Context is invalid, need to reinitialize
                logger.warning("Browser context lost. Reinitializing...")
                await self.cleanup()
                await self.initialize(headless=self.headless_mode if hasattr(self, 'headless_mode') else True)

        except Exception as e:
            logger.error(f"Error ensuring browser connection: {e}")
            # Last resort: try to reinitialize
            await self.cleanup()
            await self.initialize(headless=self.headless_mode if hasattr(self, 'headless_mode') else True)

    async def get_calculator_details(self, calculator_id: str) -> Dict:
        """
        Get calculator screenshot for visual understanding.

        Takes a screenshot of the calculator interface that Claude can analyze
        visually to understand available fields and options.

        Args:
            calculator_id (str): Calculator ID (e.g., "1752") or slug (e.g., "heart-score")

        Returns:
            Dict containing:
                - title (str): Calculator name
                - url (str): Calculator URL
                - screenshot_base64 (str): JPEG screenshot encoded as base64 (~23KB)
                - fields (List): Detected fields (informational only)

        Key Features:
            - Dynamically zooms out for long calculators to fit in viewport
            - Temporarily hides sticky Results overlay that covers bottom fields
            - Optimized JPEG compression to minimize token usage
        """
        # Ensure browser is connected before creating new page
        await self.ensure_browser_connected()

        page = await self.context.new_page()

        try:
            # Handle both numeric IDs and slugs
            if calculator_id.isdigit():
                url = f"{self.base_url}/calc/{calculator_id}"
            else:
                # Assume it's a slug and try to use it directly
                url = f"{self.base_url}/calc/{calculator_id}"

            logger.info(f"Getting details for calculator: {calculator_id}")
            await page.goto(url, wait_until='networkidle')
            await page.wait_for_timeout(3000)  # Wait longer for React to render

            # Extract calculator structure
            details = await page.evaluate('''
                () => {
                    const title = document.querySelector('h1')?.textContent?.trim();

                    // Find ALL field groups - both button-based and input-based
                    const fieldGroups = [];

                    // 1. Find button-based fields (divs with calc_option elements)
                    const allContainers = document.querySelectorAll('div');
                    allContainers.forEach(container => {
                        const options = container.querySelectorAll('div[class*="calc_option"]');

                        if (options.length > 1) {  // Must have at least 2 options to be a field
                            // Look for a label - usually a div with text right before the options
                            let label = null;
                            const firstOption = options[0];
                            let sibling = firstOption.parentElement?.previousElementSibling;

                            // Check previous siblings for a label
                            while (sibling && !label) {
                                if (sibling.textContent && sibling.children.length === 0) {
                                    const text = sibling.textContent.trim();
                                    if (text && text.length < 100) {  // Reasonable label length
                                        label = text;
                                        break;
                                    }
                                }
                                sibling = sibling.previousElementSibling;
                            }

                            // Also check if there's a label as a direct child of the parent
                            if (!label) {
                                const parentChildren = Array.from(container.children);
                                for (let child of parentChildren) {
                                    if (child.textContent && !child.classList.contains('calc_option')
                                        && child.children.length === 0) {
                                        const text = child.textContent.trim();
                                        if (text && text.length < 100) {
                                            label = text;
                                            break;
                                        }
                                    }
                                }
                            }

                            if (label && !fieldGroups.some(fg => fg.label === label)) {
                                fieldGroups.push({
                                    label: label,
                                    name: label.toLowerCase().replace(/[^a-z0-9]/g, '_'),
                                    options: Array.from(options).map(opt => ({
                                        text: opt.textContent.trim(),
                                        value: opt.textContent.trim().toLowerCase().replace(/[^a-z0-9]/g, '_'),
                                        selected: opt.className.includes('selected')
                                    }))
                                });
                            }
                        }
                    });

                    // 2. Find numeric/text input fields
                    const inputFields = document.querySelectorAll('input[type="number"], input[type="text"]:not([type="search"])');
                    inputFields.forEach(input => {
                        // Get the label for this input
                        let label = null;

                        // Try to find associated label
                        if (input.id) {
                            const labelElement = document.querySelector(`label[for="${input.id}"]`);
                            if (labelElement) {
                                label = labelElement.textContent.trim();
                            }
                        }

                        // If no label found, look for nearby text
                        if (!label) {
                            const parent = input.closest('div');
                            if (parent) {
                                // Look for text before the input
                                const walker = document.createTreeWalker(
                                    parent,
                                    NodeFilter.SHOW_TEXT,
                                    null,
                                    false
                                );
                                let node;
                                while (node = walker.nextNode()) {
                                    const text = node.textContent.trim();
                                    if (text && text.length > 1 && text.length < 50) {
                                        label = text;
                                        break;
                                    }
                                }
                            }
                        }

                        if (label) {
                            const fieldName = input.name || input.id || label.toLowerCase().replace(/[^a-z0-9]/g, '_');

                            // Check if we already have this field
                            if (!fieldGroups.some(fg => fg.name === fieldName)) {
                                fieldGroups.push({
                                    label: label,
                                    name: fieldName,
                                    type: input.type,
                                    value: input.value,
                                    placeholder: input.placeholder,
                                    options: []  // No options for input fields
                                });
                            }
                        }
                    });

                    return {
                        title,
                        fields: fieldGroups,
                        url: window.location.href
                    };
                }
            ''')

            # Take a screenshot of the calculator form
            screenshot_bytes = None
            try:
                # Measure calculator dimensions including last field position
                measurements = await page.evaluate('''
                    () => {
                        const container = document.querySelector('.side-by-side-container, .calc__body');
                        const calcHeight = container ? container.scrollHeight : 0;

                        // Find the last input field to ensure it's visible
                        const allInputs = container ? container.querySelectorAll('input, select, textarea, [class*="calc_option"]') : [];
                        let lastFieldBottom = 0;
                        if (allInputs.length > 0) {
                            const lastField = allInputs[allInputs.length - 1];
                            const rect = lastField.getBoundingClientRect();
                            const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
                            lastFieldBottom = rect.bottom + scrollTop;
                        }

                        return {
                            calcHeight: calcHeight,
                            lastFieldBottom: lastFieldBottom,
                            viewportHeight: window.innerHeight
                        };
                    }
                ''')

                calc_height = measurements['calcHeight']
                last_field_bottom = measurements['lastFieldBottom']
                viewport_height = measurements['viewportHeight']

                # Calculate optimal zoom to fit all fields in viewport
                optimal_zoom = 100
                # Use last field position if available, otherwise use container height
                target_height = last_field_bottom if last_field_bottom > 0 else calc_height

                if target_height > viewport_height:
                    # Use 90% of viewport to fit the calculator with a small margin
                    optimal_zoom = int((viewport_height / target_height) * 90)
                    optimal_zoom = max(50, min(optimal_zoom, 100))  # Clamp between 50-100%

                    # Apply zoom
                    await page.evaluate(f'() => {{ document.body.style.zoom = "{optimal_zoom}%"; }}')
                    logger.info(f"Zoomed to {optimal_zoom}% to fit calculator (height: {target_height}px) in viewport")

                # Hide sticky Results overlay that covers bottom fields
                await page.evaluate('''
                    () => {
                        // Hide Results section and any sticky/fixed overlays
                        const elements = document.querySelectorAll('[class*="result"], [class*="Result"], [class*="score"], .calc__result');
                        elements.forEach(el => {
                            el.setAttribute('data-original-display', el.style.display);
                            el.style.display = 'none';
                        });

                        // Hide sticky/fixed elements containing results
                        document.querySelectorAll('*').forEach(el => {
                            const style = window.getComputedStyle(el);
                            if ((style.position === 'sticky' || style.position === 'fixed') &&
                                (el.textContent || '').match(/Result|Score|point/)) {
                                el.setAttribute('data-original-display', el.style.display);
                                el.style.display = 'none';
                            }
                        });
                    }
                ''')

                # Scroll to top and wait for layout
                await page.evaluate('window.scrollTo(0, 0)')
                await page.wait_for_timeout(500)

                # Take screenshot (balanced quality for readability vs size)
                screenshot_bytes = await page.screenshot(
                    type='jpeg',
                    quality=60,  # Consistent quality for all screenshots
                    full_page=False  # Viewport only
                )

                # Restore hidden elements and zoom
                await page.evaluate('''
                    () => {
                        // Restore visibility
                        document.querySelectorAll('[data-original-display]').forEach(el => {
                            el.style.display = el.getAttribute('data-original-display') || '';
                            el.removeAttribute('data-original-display');
                        });
                        // Reset zoom to 100%
                        document.body.style.zoom = '100%';
                    }
                ''')

                # Convert to base64
                if screenshot_bytes:
                    details['screenshot_base64'] = base64.b64encode(screenshot_bytes).decode('utf-8')
                    logger.info(f"Screenshot captured: {len(screenshot_bytes)} bytes ({len(details['screenshot_base64']) // 1024}KB base64)")

            except Exception as e:
                logger.warning(f"Failed to capture screenshot: {e}")

            logger.info(f"Found {len(details.get('fields', []))} fields for {details.get('title', 'Unknown')}")
            return details

        finally:
            # Keep page open for user to review while looking at field inventory/mappings
            # await page.close()
            pass

    async def execute_calculator(self, calculator_id: str, inputs: Dict) -> Dict:
        """
        Execute calculator with provided input values.

        Args:
            calculator_id (str): Calculator ID (e.g., "1752") or slug (e.g., "heart-score")
            inputs (Dict): Field values mapped to calculator inputs:
                - Keys: Field names as shown in calculator
                - Values: EXACT button text or numeric values

                Examples:
                    {"Age": "≥65", "History": "Moderately suspicious"}
                    {"Total Cholesterol": "200", "HDL": "45"}

        Returns:
            Dict containing:
                - success (bool): Whether calculation succeeded
                - score (str): Calculated score (if extracted)
                - risk (str): Risk category or percentage (if found)
                - interpretation (str): Clinical meaning (if found)
                - result_screenshot_base64 (str): JPEG screenshot of entire form with results
                  Shows all inputs and results with smart zoom to fit everything.
                  Enables agent to visually see conditional fields and results.

        Note:
            Must use EXACT text as shown in calculator buttons.
            Call get_calculator_details first to see available options.
        """
        # Ensure browser is connected before creating new page
        await self.ensure_browser_connected()

        page = await self.context.new_page()

        try:
            # Navigate to calculator
            if calculator_id.isdigit():
                url = f"{self.base_url}/calc/{calculator_id}"
            else:
                # Assume it's a slug and try to use it directly
                url = f"{self.base_url}/calc/{calculator_id}"

            logger.info(f"Executing calculator: {calculator_id}")
            await page.goto(url, wait_until='networkidle')
            await page.wait_for_timeout(2000)  # Wait for React to render


            # Fill inputs and click buttons based on input values
            for field_name, value in inputs.items():
                logger.info(f"Setting {field_name} to '{value}'")
                filled = False

                # Check if value is numeric - if so, try input fields first
                try:
                    float(str(value))  # Convert to string first in case it's not
                    is_numeric_value = True
                except (ValueError, TypeError):
                    is_numeric_value = False

                logger.info(f"  Field type detection: is_numeric_value={is_numeric_value}")

                # For numeric values, always try input fields first
                # The screenshot will show which fields are inputs vs buttons
                if is_numeric_value:
                    logger.info(f"  Value '{value}' is numeric, trying input fields first")

                    # ====================================================================================
                    # STRATEGY 0: Playwright Native Methods (THE PRIMARY SOLUTION)
                    # This is the main working approach for numeric inputs in React forms.
                    # MDCalc follows a consistent pattern where the HTML 'name' attribute
                    # is the lowercase version of the field label.
                    # Example: "Age" → name="age", "Serum Sodium" → name="serumsodium"
                    # We use Playwright's type() method with delays to properly trigger React validation.
                    # ====================================================================================
                    field_name_lower = field_name.lower().replace(' ', '')
                    selectors = [
                        f'input[name="{field_name_lower}"]',  # Exact name attribute
                        f'input[placeholder*="{field_name}" i]',  # Placeholder text
                    ]

                    for selector in selectors:
                        try:
                            elements = await page.locator(selector).all()
                            for elem in elements:
                                if await elem.is_visible():
                                    # Click to focus
                                    await elem.click()
                                    # Clear and type with delay to trigger React events
                                    await elem.fill('')
                                    await elem.type(str(value), delay=100)  # Type each character with 100ms delay
                                    # Press Tab to trigger blur
                                    await elem.press('Tab')
                                    filled = True
                                    logger.info(f"  ✅ Filled using Playwright native type: {field_name} = {value}")
                                    break
                            if filled:
                                break
                        except Exception as e:
                            logger.debug(f"  Playwright selector {selector} failed: {e}")
                            continue

                    if filled:
                        await asyncio.sleep(0.5)  # Give React time to update
                        continue

                    # ====================================================================================
                    # FALLBACK STRATEGIES: JavaScript-based field filling
                    # These strategies run if Playwright native methods fail.
                    # They use complex label-to-input association logic to find the right field.
                    # While these didn't solve the React validation issue for Creatinine Clearance,
                    # they remain useful fallbacks for other calculator patterns.
                    # ====================================================================================
                    # Strategy 1: Find the CORRECT input field by better field-to-input association
                    try:
                        # Look for the field label and find associated input
                        # Pass parameters as a single object
                        filled = await page.evaluate('''({fieldName, value}) => {

                            // First, collect ALL visible inputs on the page with their positions
                            const allInputs = Array.from(document.querySelectorAll('input[type="text"], input[type="number"], input:not([type])')).filter(inp => {
                                const rect = inp.getBoundingClientRect();
                                return rect.width > 0 && rect.height > 0 && !inp.disabled && !inp.readOnly;
                            }).map(input => {
                                const rect = input.getBoundingClientRect();
                                return {
                                    element: input,
                                    top: rect.top,
                                    left: rect.left,
                                    placeholder: input.placeholder || '',
                                    value: input.value || '',
                                    id: input.id || '',
                                    name: input.name || ''
                                };
                            });


                            // Find elements that contain the field name - be more precise
                            const labels = Array.from(document.querySelectorAll('*')).filter(el => {
                                const text = (el.textContent || '').trim();
                                // Only consider elements that directly contain the text (not in children)
                                const directText = Array.from(el.childNodes)
                                    .filter(node => node.nodeType === Node.TEXT_NODE)
                                    .map(node => node.textContent.trim())
                                    .join(' ').trim();

                                // Match if the direct text is exactly or starts with the field name
                                return (directText === fieldName ||
                                       directText.startsWith(fieldName) ||
                                       text === fieldName) &&
                                       text.length < fieldName.length + 100 &&
                                       el.tagName !== 'SCRIPT' &&
                                       el.tagName !== 'STYLE';
                            });


                            // Sort labels by specificity and position
                            labels.sort((a, b) => {
                                const aText = a.textContent.trim();
                                const bText = b.textContent.trim();
                                const aRect = a.getBoundingClientRect();
                                const bRect = b.getBoundingClientRect();

                                // Exact match gets highest priority
                                if (aText === fieldName && bText !== fieldName) return -1;
                                if (bText === fieldName && aText !== fieldName) return 1;

                                // Then prefer elements higher on the page (smaller top value)
                                if (Math.abs(aRect.top - bRect.top) > 10) {
                                    return aRect.top - bRect.top;
                                }

                                // Then prefer shorter text (less extra content)
                                return aText.length - bText.length;
                            });

                            for (const label of labels) {
                                // First check if this label element has a direct 'for' attribute
                                if (label.tagName === 'LABEL' && label.getAttribute('for')) {
                                    const inputId = label.getAttribute('for');
                                    const input = document.getElementById(inputId);
                                    if (input) {
                                        // Fill and return

                                        // Simulate real user typing
                                        input.focus();
                                        input.select();

                                        // Clear existing value first
                                        input.value = '';
                                        input.dispatchEvent(new Event('input', { bubbles: true }));

                                        // Type each character
                                        for (let char of value.toString()) {
                                            input.value += char;
                                            input.dispatchEvent(new KeyboardEvent('keydown', { key: char, bubbles: true }));
                                            input.dispatchEvent(new KeyboardEvent('keypress', { key: char, bubbles: true }));
                                            input.dispatchEvent(new Event('input', { bubbles: true }));
                                            input.dispatchEvent(new KeyboardEvent('keyup', { key: char, bubbles: true }));
                                        }

                                        // Trigger change and blur
                                        input.dispatchEvent(new Event('change', { bubbles: true }));
                                        input.blur();
                                        input.dispatchEvent(new Event('blur', { bubbles: true }))

                                        return true;
                                    }
                                }

                                // Look for the CLOSEST input field to this label
                                // Start from the label itself and search siblings and parent containers

                                // Check immediate siblings first
                                let nextSibling = label.nextElementSibling;
                                while (nextSibling && nextSibling.nodeType === 1) {
                                    if (nextSibling.tagName === 'INPUT' &&
                                        (nextSibling.type === 'text' || nextSibling.type === 'number' || !nextSibling.type)) {
                                        const rect = nextSibling.getBoundingClientRect();
                                        if (rect.width > 0 && rect.height > 0 && !nextSibling.disabled && !nextSibling.readOnly) {
                                            // Check if this input is already filled
                                            if (nextSibling.value && nextSibling.value !== '' && nextSibling.value !== value) {
                                                break;
                                            }
                                            // Simulate real user typing
                                            nextSibling.focus();
                                            nextSibling.select();

                                            // Clear existing value first
                                            nextSibling.value = '';
                                            nextSibling.dispatchEvent(new Event('input', { bubbles: true }));

                                            // Type each character
                                            for (let char of value.toString()) {
                                                nextSibling.value += char;
                                                nextSibling.dispatchEvent(new KeyboardEvent('keydown', { key: char, bubbles: true }));
                                                nextSibling.dispatchEvent(new KeyboardEvent('keypress', { key: char, bubbles: true }));
                                                nextSibling.dispatchEvent(new Event('input', { bubbles: true }));
                                                nextSibling.dispatchEvent(new KeyboardEvent('keyup', { key: char, bubbles: true }));
                                            }

                                            // Trigger change and blur
                                            nextSibling.dispatchEvent(new Event('change', { bubbles: true }));
                                            nextSibling.blur();
                                            nextSibling.dispatchEvent(new Event('blur', { bubbles: true }));

                                            return true;
                                        }
                                    }
                                    // Check if next sibling contains an input
                                    const inputInSibling = nextSibling.querySelector('input[type="text"], input[type="number"], input:not([type])');
                                    if (inputInSibling) {
                                        const rect = inputInSibling.getBoundingClientRect();
                                        if (rect.width > 0 && rect.height > 0 && !inputInSibling.disabled && !inputInSibling.readOnly) {
                                            // Check if already filled
                                            if (inputInSibling.value && inputInSibling.value !== '' && inputInSibling.value !== value) {
                                                break;
                                            }

                                            // Simulate real user typing
                                            inputInSibling.focus();
                                            inputInSibling.select();

                                            // Clear existing value first
                                            inputInSibling.value = '';
                                            inputInSibling.dispatchEvent(new Event('input', { bubbles: true }));

                                            // Type each character
                                            for (let char of value.toString()) {
                                                inputInSibling.value += char;
                                                inputInSibling.dispatchEvent(new KeyboardEvent('keydown', { key: char, bubbles: true }));
                                                inputInSibling.dispatchEvent(new KeyboardEvent('keypress', { key: char, bubbles: true }));
                                                inputInSibling.dispatchEvent(new Event('input', { bubbles: true }));
                                                inputInSibling.dispatchEvent(new KeyboardEvent('keyup', { key: char, bubbles: true }));
                                            }

                                            // Trigger change and blur
                                            inputInSibling.dispatchEvent(new Event('change', { bubbles: true }));
                                            inputInSibling.blur();
                                            inputInSibling.dispatchEvent(new Event('blur', { bubbles: true }));

                                            return true;
                                        }
                                    }
                                    nextSibling = nextSibling.nextElementSibling;
                                }

                                // Find the closest UNFILLED input to this label
                                const labelRect = label.getBoundingClientRect();

                                // Find all unfilled inputs and calculate their distance to this label
                                const unfilledInputs = allInputs.filter(inp => !inp.value || inp.value === '');

                                if (unfilledInputs.length > 0) {
                                    // Calculate distance for each unfilled input
                                    const inputsWithDistance = unfilledInputs.map(inp => {
                                        // Calculate Euclidean distance but prioritize vertical alignment
                                        const verticalDist = Math.abs(inp.top - labelRect.top);
                                        const horizontalDist = Math.abs(inp.left - labelRect.left);
                                        // Weight vertical distance less since labels are often above/below inputs
                                        const distance = Math.sqrt(verticalDist * verticalDist + horizontalDist * horizontalDist * 0.5);
                                        return {
                                            ...inp,
                                            distance: distance,
                                            verticalDist: verticalDist
                                        };
                                    });

                                    // Sort by distance and find the closest one
                                    inputsWithDistance.sort((a, b) => a.distance - b.distance);

                                    const closest = inputsWithDistance[0];

                                    // Only fill if the closest input is reasonably close (within 200px)
                                    if (closest && closest.distance < 300) {

                                        const input = closest.element;
                                        // Simulate real user typing
                                        input.focus();
                                        input.select();

                                        // Clear existing value first
                                        input.value = '';
                                        input.dispatchEvent(new Event('input', { bubbles: true }));

                                        // Type each character
                                        for (let char of value.toString()) {
                                            input.value += char;
                                            input.dispatchEvent(new KeyboardEvent('keydown', { key: char, bubbles: true }));
                                            input.dispatchEvent(new KeyboardEvent('keypress', { key: char, bubbles: true }));
                                            input.dispatchEvent(new Event('input', { bubbles: true }));
                                            input.dispatchEvent(new KeyboardEvent('keyup', { key: char, bubbles: true }));
                                        }

                                        // Trigger change and blur
                                        input.dispatchEvent(new Event('change', { bubbles: true }));
                                        input.blur();
                                        input.dispatchEvent(new Event('blur', { bubbles: true }));

                                        return true;
                                    }
                                }
                            }

                            return false;
                        }''', {'fieldName': field_name, 'value': str(value)})

                        if filled:
                            logger.info(f"  ✅ Filled numeric input field: {field_name} = {value}")
                            # Wait a bit for React to recalculate derived values (like P/F ratio)
                            await page.wait_for_timeout(500)
                        else:
                            logger.info(f"  Could not find input field for numeric value {field_name}")
                    except Exception as e:
                        logger.warning(f"  Strategy 1 (find input near label) failed: {e}")

                    # Strategy 2: Try various generic selectors (no calculator-specific patterns)
                    if not filled:
                        input_selectors = [
                            # Standard patterns based on field name
                            f'input[placeholder*="{field_name}"]',
                            f'input[aria-label*="{field_name}"]',
                            f'input[name="{field_name.lower().replace(" ", "_")}"]',
                            f'input[name="{field_name.lower().replace(" ", "")}"]',

                            # Generic numeric input patterns
                            'input[type="number"]',
                            'input[type="text"][inputmode="decimal"]',
                            'input[type="text"][inputmode="numeric"]'
                        ]

                        for selector in input_selectors:
                            try:
                                elements = page.locator(selector)
                                count = await elements.count()
                                if count > 0:
                                    # If there are multiple, try to find the right one by context
                                    if count == 1:
                                        await elements.first.fill(str(value))
                                        filled = True
                                        logger.info(f"  ✅ Filled input field: {field_name} = {value}")
                                        break
                                    else:
                                        # Multiple matches - find the one near our field label
                                        for i in range(count):
                                            element = elements.nth(i)
                                            is_correct = await element.evaluate('''(el, fieldName) => {
                                                // Check if this input is near the field name
                                                const container = el.closest('div[class*="field"], div[class*="input"], .form-group, .input-group');
                                                if (container && container.textContent.includes(fieldName)) {
                                                    return true;
                                                }
                                                // Check previous sibling for label
                                                const label = el.previousElementSibling;
                                                if (label && label.textContent.includes(fieldName)) {
                                                    return true;
                                                }
                                                return false;
                                            }''', field_name)

                                            if is_correct:
                                                await element.fill(str(value))
                                                filled = True
                                                logger.info(f"  ✅ Filled input field (context match): {field_name} = {value}")
                                                break

                                        if filled:
                                            break
                            except Exception as e:
                                logger.debug(f"  Input selector '{selector}' failed: {e}")
                                pass

                # If not filled, try button clicking
                if not filled:
                    button_text = str(value)
                    logger.info(f"  🔍 Starting button click for field '{field_name}'")
                    logger.info(f"  🔍 Original value: '{button_text}'")

                    # Store original for comparison
                    original_text = button_text

                    # Convert hyphens to en dashes for decimal ranges (MDCalc pattern)
                    # Pattern: decimal ranges use en dashes (2.0–5.9), integer ranges use hyphens (50-99)
                    # Match decimal number, hyphen, decimal number (e.g., 2.0-5.9, 1.2-1.9)
                    decimal_pattern = r'(\d+\.\d+)-(\d+\.\d+)'

                    # Check if pattern matches
                    match = re.search(decimal_pattern, button_text)
                    logger.info(f"  🔍 Checking for decimal pattern match: {bool(match)}")
                    if match:
                        logger.info(f"  🔍 Found decimal range: '{match.group()}'")

                    # Replace hyphen with en dash (U+2013) only for decimal ranges
                    button_text = re.sub(decimal_pattern, r'\1–\2', button_text)

                    # Log character codes for debugging
                    if '–' in button_text:
                        logger.info(f"  🔍 En dash found in converted text at position {button_text.index('–')}")
                    if '-' in original_text:
                        logger.info(f"  🔍 Hyphen found in original text at position {original_text.index('-')}")

                    if button_text != original_text:
                        logger.info(f"  ✅ Converted '{original_text}' to '{button_text}'")
                        # Log character codes for the dash
                        for i, (o_char, c_char) in enumerate(zip(original_text, button_text)):
                            if o_char != c_char:
                                logger.info(f"  🔍 Char diff at position {i}: '{o_char}' (code {ord(o_char)}) → '{c_char}' (code {ord(c_char)})")
                    else:
                        logger.info(f"  🔍 No conversion needed for '{button_text}'")

                    clicked = False

                    # Strategy 1: Direct button text
                    try:
                        logger.info(f"  🔄 Strategy 1: Looking for button with text '{button_text}'")
                        button_selector = f"button:has-text('{button_text}')"
                        count = await page.locator(button_selector).count()
                        logger.info(f"  🔄 Strategy 1: Found {count} buttons with text '{button_text}'")
                        if count > 0:
                            await page.click(button_selector)
                            clicked = True
                            logger.info(f"  ✅ Strategy 1: Successfully clicked button: {button_text}")
                    except Exception as e:
                        logger.info(f"  ❌ Strategy 1 failed: {e}")

                    # Strategy 2: Any clickable div with exact text (MDCalc uses divs for buttons)
                    if not clicked:
                        try:
                            logger.info(f"  🔄 Strategy 2: Looking for div with exact text '{button_text}'")
                            # MDCalc uses divs as buttons, not actual button elements
                            # Use text= for exact match, find the innermost element
                            option_selector = f"div:text-is('{button_text}')"  # Exact text match
                            elements = page.locator(option_selector)
                            count = await elements.count()
                            logger.info(f"  🔄 Strategy 2: Found {count} divs with exact text '{button_text}'")

                            # If there's only one element, click it (no ambiguity)
                            if count == 1:
                                element = elements.first
                                # Check if already selected - check both CSS classes and background colors
                                element_info = await element.evaluate('''el => {
                                    // Strategy 1: Check CSS classes (common pattern)
                                    // MDCalc uses class patterns like "calc_btn-selected" for selected state
                                    let checkElement = el;
                                    let maxLevels = 3;
                                    let hasSelectedClass = false;

                                    while (checkElement && maxLevels > 0) {
                                        const classes = checkElement.className || '';

                                        // Check if this element has selection indicators
                                        if (classes.includes('selected') ||
                                            classes.includes('active') ||
                                            classes.includes('checked')) {
                                            hasSelectedClass = true;
                                            break;
                                        }

                                        checkElement = checkElement.parentElement;
                                        maxLevels--;
                                    }

                                    // PRE-SELECTION DETECTION: Check background colors (for calculators that use color styling)
                                    // MDCalc uses teal (rgb(26, 188, 156)) for selected state
                                    const style = window.getComputedStyle(el);
                                    const bgColor = style.backgroundColor;
                                    const parentBg = el.parentElement ?
                                        window.getComputedStyle(el.parentElement).backgroundColor : '';

                                    // Check for teal/green selected state (rgb(26, 188, 156))
                                    const hasTealBg = bgColor === 'rgb(26, 188, 156)' ||
                                                     bgColor === 'rgba(26, 188, 156, 1)' ||
                                                     parentBg === 'rgb(26, 188, 156)' ||
                                                     parentBg === 'rgba(26, 188, 156, 1)';

                                    return {
                                        isSelected: hasSelectedClass || hasTealBg,
                                        hasClass: hasSelectedClass,
                                        hasColor: hasTealBg,
                                        classes: el.className || '',
                                        bgColor: bgColor
                                    };
                                }''')

                                logger.info(f"  🔍 Element state: selected={element_info['isSelected']} (class={element_info['hasClass']}, color={element_info['hasColor']}), classes='{element_info['classes']}'")
                                element_state = element_info['isSelected']

                                if element_state:
                                    clicked = True
                                    logger.info(f"  ✅ Strategy 2: Option already selected (skipping click): {button_text}")
                                else:
                                    await element.click()
                                    clicked = True
                                    logger.info(f"  ✅ Strategy 2: Successfully clicked option: {button_text}")
                            elif count > 1:
                                # Multiple elements found - skip to Strategy 3 for context-aware clicking
                                logger.info(f"  ⚠️ Strategy 2: Multiple elements ({count}) found, need context-aware selection")
                            else:
                                logger.info(f"  ⚠️ Strategy 2: No elements found")
                        except Exception as e:
                            logger.info(f"  ❌ Strategy 2 failed: {e}")

                    # Strategy 3: Context-aware search - find button near the field label
                    if not clicked:
                        # The field_name should be the exact label seen in the UI
                        logger.info(f"  🔄 Strategy 3: Looking for '{button_text}' button near field '{field_name}'")

                        try:
                            # For complex text with special characters, escape them for CSS selectors
                            # But first try without escaping
                            button_locator = page.locator(f"button:text-is('{button_text}'), div:text-is('{button_text}')")
                            all_buttons = await button_locator.element_handles()

                            # If no exact match found, try with partial text matching
                            if len(all_buttons) == 0:
                                # Try contains text for complex strings
                                button_locator = page.locator(f"button:has-text('{button_text}'), div:has-text('{button_text}')")
                                all_buttons = await button_locator.element_handles()

                            logger.info(f"  🔄 Strategy 3: Found {len(all_buttons)} elements with text '{button_text}'")

                            for button in all_buttons:
                                # Check if this button is near the field label
                                is_in_field = await button.evaluate('''(el, fieldName) => {
                                    // Walk up the DOM to find if we're in the right field
                                    let parent = el.parentElement;
                                    let maxLevels = 5;  // Only go up 5 levels for speed
                                    while (parent && maxLevels > 0) {
                                        // Check if the parent contains the field name
                                        if (parent.textContent.includes(fieldName)) {
                                            return true;
                                        }
                                        parent = parent.parentElement;
                                        maxLevels--;
                                    }
                                    return false;
                                }''', field_name)

                                if is_in_field:
                                    # Check if already selected using both class names and colors
                                    button_state = await button.evaluate('''el => {
                                        // Check 1: CSS classes
                                        let checkElement = el;
                                        let maxLevels = 3;
                                        let hasSelectedClass = false;

                                        while (checkElement && maxLevels > 0) {
                                            const classes = checkElement.className || '';
                                            if (classes.includes('selected') ||
                                                classes.includes('active') ||
                                                classes.includes('checked')) {
                                                hasSelectedClass = true;
                                                break;
                                            }
                                            checkElement = checkElement.parentElement;
                                            maxLevels--;
                                        }

                                        // Check 2: Background colors
                                        const bgColor = window.getComputedStyle(el).backgroundColor;
                                        const parentBg = el.parentElement ?
                                            window.getComputedStyle(el.parentElement).backgroundColor : '';

                                        const hasTealBg = bgColor === 'rgb(26, 188, 156)' ||
                                                         bgColor === 'rgba(26, 188, 156, 1)' ||
                                                         parentBg === 'rgb(26, 188, 156)' ||
                                                         parentBg === 'rgba(26, 188, 156, 1)';

                                        return hasSelectedClass || hasTealBg;
                                    }''')

                                    if button_state:
                                        clicked = True
                                        logger.info(f"  ✅ Strategy 3: Button already selected (skipping click) for field '{field_name}': {button_text}")
                                    else:
                                        await button.click()
                                        clicked = True
                                        logger.info(f"  ✅ Strategy 3: Successfully clicked {button_text} for field '{field_name}'")
                                    break

                        except Exception as e:
                            logger.info(f"  ❌ Strategy 3 failed: {e}")

                    # Strategy 4: Use JavaScript to find and click the button
                    if not clicked:
                        logger.info(f"  🔄 Strategy 4: Using JavaScript to find '{button_text}' near '{field_name}'")
                        try:
                            clicked = await page.evaluate('''({fieldName, buttonText}) => {

                                // Find all clickable elements (buttons and divs that act as buttons)
                                const allClickables = Array.from(document.querySelectorAll('button, div[role="button"], div[class*="option"], div[class*="button"], div[onclick]'));

                                for (const element of allClickables) {
                                    const elementText = element.textContent?.trim();

                                    // Check for exact match or contains the text
                                    if (elementText === buttonText ||
                                        (elementText && elementText.includes(buttonText))) {

                                        // Check if this element is near the field label
                                        let parent = element;
                                        let foundNearField = false;

                                        for (let i = 0; i < 5; i++) {
                                            parent = parent.parentElement;
                                            if (!parent) break;

                                            if (parent.textContent && parent.textContent.includes(fieldName)) {
                                                foundNearField = true;
                                                break;
                                            }
                                        }

                                        if (foundNearField) {

                                            // Check if not already selected (both class and color)
                                            // Check 1: CSS classes
                                            let checkEl = element;
                                            let hasSelectedClass = false;
                                            for (let i = 0; i < 3 && checkEl; i++) {
                                                const classes = checkEl.className || '';
                                                if (classes.includes('selected') ||
                                                    classes.includes('active') ||
                                                    classes.includes('checked')) {
                                                    hasSelectedClass = true;
                                                    break;
                                                }
                                                checkEl = checkEl.parentElement;
                                            }

                                            // Check 2: Background color
                                            const bgColor = window.getComputedStyle(element).backgroundColor;
                                            const hasTealBg = bgColor === 'rgb(26, 188, 156)' ||
                                                            bgColor === 'rgba(26, 188, 156, 1)';

                                            const isSelected = hasSelectedClass || hasTealBg;

                                            if (isSelected) {
                                                return true;
                                            }

                                            element.click();
                                            return true;
                                        }
                                    }
                                }

                                return false;
                            }''', {'fieldName': field_name, 'buttonText': button_text})

                            if clicked:
                                logger.info(f"  ✅ Strategy 4: Successfully clicked option via JavaScript: {button_text}")
                            else:
                                logger.info(f"  ❌ Strategy 4: JavaScript could not find matching button")
                        except Exception as e:
                            logger.info(f"  ❌ Strategy 4 (JavaScript click) failed: {e}")

                    if not clicked:
                        logger.warning(f"  ⚠️ Could not click option for {field_name}: {button_text}")

                # Wait for React to update and any conditional fields to appear
                # Some calculators show/hide fields based on selections (like APACHE II)
                if field_name.lower() in ['fio₂', 'fio2']:
                    # Wait longer after FiO₂ as it triggers conditional fields
                    await page.wait_for_timeout(1000)
                else:
                    await page.wait_for_timeout(100)

            # Wait for results to update (MDCalc takes time to calculate)
            # Increased timeout to ensure React has processed all input events
            await page.wait_for_timeout(3000)

            # Take a screenshot of the result (for agent to see what happened)
            result_screenshot_base64 = None
            try:
                # Measure everything including results to capture full view
                measurements_with_results = await page.evaluate('''
                    () => {
                        // Find all content including inputs AND results
                        const allElements = document.querySelectorAll('input, select, textarea, [class*="calc_option"], [class*="result"], [class*="Result"], [class*="score"], [class*="Score"]');

                        let maxBottom = 0;
                        allElements.forEach(el => {
                            const rect = el.getBoundingClientRect();
                            const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
                            const bottom = rect.bottom + scrollTop;
                            if (bottom > maxBottom) maxBottom = bottom;
                        });

                        // Also check the calc body container
                        const container = document.querySelector('.side-by-side-container, .calc__body, body');
                        const containerHeight = container ? container.scrollHeight : 0;

                        return {
                            contentHeight: Math.max(maxBottom, containerHeight),
                            viewportHeight: window.innerHeight
                        };
                    }
                ''')

                content_height = measurements_with_results['contentHeight']
                viewport_height = measurements_with_results['viewportHeight']

                # Calculate zoom but prioritize readability
                # Don't zoom out too much - better to have partial view that's readable
                if content_height > viewport_height:
                    optimal_zoom = int((viewport_height / content_height) * 90)  # 90% to leave margin
                    # Keep minimum 60% zoom for readability (was 40%)
                    optimal_zoom = max(60, min(optimal_zoom, 100))
                    await page.evaluate(f'() => {{ document.body.style.zoom = "{optimal_zoom}%"; }}')
                    logger.info(f"Zoomed result view to {optimal_zoom}% to fit content (height: {content_height}px)")
                    await page.wait_for_timeout(500)  # Wait for zoom to apply

                # Scroll to top to capture from beginning
                await page.evaluate('window.scrollTo(0, 0)')
                await page.wait_for_timeout(300)

                # Take a single screenshot that serves both purposes
                # Use quality that's good for both agent viewing and test debugging
                result_screenshot = await page.screenshot(
                    type='jpeg',
                    quality=60,  # Balance between agent needs (50%) and test needs (85%)
                    full_page=False  # Viewport capture with zoom applied
                )

                # Convert to base64 for agent to see
                result_screenshot_base64 = base64.b64encode(result_screenshot).decode('utf-8')
                logger.info(f"Result screenshot captured: {len(result_screenshot)} bytes ({len(result_screenshot_base64) // 1024}KB base64)")

                # Save the SAME screenshot to test directory if it exists
                screenshots_dir = Path(__file__).parent.parent / "tests" / "screenshots"
                if screenshots_dir.exists():
                    result_path = screenshots_dir / f"{calculator_id}_result.jpg"
                    with open(result_path, 'wb') as f:
                        f.write(result_screenshot)  # Save the exact same screenshot
                    logger.info(f"📸 Result screenshot saved to: {result_path}")
            except Exception as e:
                logger.warning(f"Could not capture result screenshot: {e}")
                # Even on error, try to capture current state for agent
                try:
                    error_screenshot = await page.screenshot(
                        type='jpeg',
                        quality=60,  # Consistent quality even for error screenshots
                        full_page=False
                    )
                    result_screenshot_base64 = base64.b64encode(error_screenshot).decode('utf-8')
                except:
                    pass

            # Extract results - look for result containers and score displays
            results = await page.evaluate('''
                () => {
                    let score = null;
                    let risk = null;
                    let interpretation = null;

                    // Strategy 1: Look for result containers (calc_result class pattern)
                    // MDCalc consistently uses classes with "calc_result" in them
                    const resultContainers = document.querySelectorAll('[class*="calc_result"], [class*="result_container"], [class*="score_display"], [class*="calc-results"]');

                    for (const container of resultContainers) {
                        // Look for heading elements (h1, h2, h3) within the result container
                        // These typically contain the score
                        const headings = container.querySelectorAll('h1, h2, h3, h4, div[class*="score"]');
                        for (const heading of headings) {
                            const text = heading.textContent.trim();
                            // Match patterns like "8 points", "8", "SOFA Score: 8", etc.
                            const scoreMatch = text.match(/(\\d+)\\s*(points?|pts?)?/i);
                            if (scoreMatch && !score) {
                                score = scoreMatch[1] + ' points';

                                // Also look for risk/interpretation in the same container
                                const containerText = container.textContent;
                                // Extract risk percentage if present
                                const riskMatch = containerText.match(/(\\d+\\.?\\d*)%.*?(risk|mortality|per year)/i);
                                if (riskMatch && !risk) {
                                    risk = riskMatch[0];
                                }
                                break;
                            }
                        }
                        if (score) break; // Found score, stop looking
                    }

                    // Strategy 2: If no result container found, look for prominent score displays
                    if (!score) {
                        // Look for large text elements containing scores
                        const allElements = document.querySelectorAll('div, span, h1, h2, h3, p');
                        for (const el of allElements) {
                            const text = el.textContent.trim();

                            // Skip long text (definitely not a score)
                            if (text.length > 50) continue;

                            // Check if it matches score pattern
                            const scoreMatch = text.match(/^(\\d+)\\s*(points?|pts?)?$/i);
                            if (scoreMatch) {
                                // Verify it's prominently displayed
                                const style = window.getComputedStyle(el);
                                const fontSize = parseFloat(style.fontSize);
                                const isVisible = style.display !== 'none' && style.visibility !== 'hidden';

                                if (isVisible && fontSize >= 24) { // Large font for scores
                                    score = scoreMatch[1] + ' points';
                                    break;
                                }
                            }
                        }
                    }

                    // Look for interpretation (Low/Moderate/High Score)
                    if (!interpretation) {
                        const interpElements = document.querySelectorAll('*');
                        for (const el of interpElements) {
                            const text = el.textContent.trim();
                            if (text.length < 100) {
                                const match = text.match(/(Low|Moderate|High)\\s*(Score|Risk)\\s*\\(?(\\d+-?\\d*\\s*points?)\\)?/i);
                                if (match) {
                                    interpretation = match[0];
                                    break;
                                }
                            }
                        }
                    }

                    // Strategy 3: Look for any visible score or result pattern
                    if (!score) {
                        // Get all visible text
                        const visibleText = document.body.innerText || document.body.textContent;

                        // Look for common patterns (generic, not calculator-specific)
                        // Pattern 1: "X points" or "X pts" anywhere in visible text
                        const pointsPattern = visibleText.match(/(\\d+)\\s+(?:points?|pts?)(?!\\s*[\\+\\-])/i);
                        if (pointsPattern) {
                            score = pointsPattern[1] + ' points';
                        } else {
                            // Pattern 2: Look for "Score: X" or similar
                            const scorePattern = visibleText.match(/Score[:\\s]+(\\d+)/i);
                            if (scorePattern) {
                                score = scorePattern[1] + ' points';
                            } else {
                                // Pattern 3: For calculators like LDL that show a value with units
                                // Look for patterns like "125 mg/dL" or "LDL: 125"
                                const valuePattern = visibleText.match(/(\\d+\\.?\\d*)\\s*(?:mg\\/dL|mmol\\/L)/i);
                                if (valuePattern) {
                                    score = valuePattern[1] + ' mg/dL';
                                }
                            }
                        }
                    }

                    return {
                        score: score,
                        risk: risk,
                        interpretation: interpretation,
                        success: !!(score || risk)
                    };
                }
            ''')

            # Always include the result screenshot so agent can see what happened
            results['result_screenshot_base64'] = result_screenshot_base64

            if results['success']:
                logger.info(f"✅ Calculation successful: {results.get('score', 'N/A')}")
            else:
                logger.warning("⚠️ Could not extract results (may be auto-calculated)")
                logger.info("Screenshot included for agent to visually interpret results")

            return results

        finally:
            # Keep page open for user to review while looking at field inventory/mappings
            # await page.close()
            pass

    async def cleanup(self):
        """Clean up browser resources."""
        if self.browser:
            await self.browser.close()
            self.browser = None
        if self.context:
            self.context = None
        if self.playwright:
            await self.playwright.stop()
            self.playwright = None
        logger.info("Browser cleanup complete")


# Quick test
if __name__ == "__main__":
    async def quick_test():
        client = MDCalcClient()
        await client.initialize(headless=False)

        # Test search
        results = await client.search_calculators("heart")
        logger.info(f"Search found {len(results)} calculators")
        if results:
            logger.info(f"First: {results[0]['title']}")

        # Test details
        details = await client.get_calculator_details("1752")
        logger.info(f"Calculator: {details.get('title', 'Unknown')}")
        logger.info(f"Fields: {len(details.get('fields', []))}")

        # Test execution
        inputs = {
            'history': 'slightly_suspicious',
            'age': '45-64',
            'ecg': 'normal',
            'risk_factors': '1-2',
            'troponin': 'normal'
        }

        result = await client.execute_calculator("1752", inputs)
        logger.info(f"Result: {result}")

        await client.cleanup()

    asyncio.run(quick_test())