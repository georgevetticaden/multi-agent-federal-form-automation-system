"""
Playwright client for browser automation in FederalScout.

Implements critical patterns learned from FSA testing:
- Hidden radio buttons need JavaScript click
- Typeahead fields need fill + Enter keypress  
- Wait for state='attached' for hidden elements
- Full-page screenshots with optimization

Reference: requirements/discovery/PLAYWRIGHT_PATTERNS.md
"""

import asyncio
import base64
import io
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timedelta

from playwright.async_api import (
    async_playwright,
    Browser,
    Page,
    Playwright,
    TimeoutError as PlaywrightTimeoutError
)
from PIL import Image

from config import FederalScoutConfig, get_config
from logging_config import get_logger, log_browser_action
from models import InteractionType, SelectorType


logger = get_logger(__name__)


class PlaywrightClient:
    """
    Playwright browser automation client.
    
    Manages browser instances, page interactions, and screenshot capture
    with patterns optimized for government form wizards.
    """
    
    def __init__(self, config: Optional[FederalScoutConfig] = None):
        """
        Initialize Playwright client.

        Args:
            config: FederalScout configuration (uses default if None)
        """
        self.config = config or get_config()
        self.playwright: Optional[Playwright] = None
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self._is_launched = False
        
    async def launch(self) -> Browser:
        """
        Launch Playwright browser or connect to existing one.

        If browser_endpoint is configured, connects to existing browser (demo mode).
        Otherwise, launches a new browser.

        Returns:
            Browser instance
        """
        if self._is_launched and self.browser:
            return self.browser

        self.playwright = await async_playwright().start()

        # Check if we should connect to existing browser (demo mode)
        if self.config.browser_endpoint:
            logger.info(f"Connecting to existing browser at {self.config.browser_endpoint}")
            try:
                # Connect via HTTP endpoint (Playwright will auto-discover WebSocket)
                # This works with predefined endpoints like http://localhost:9222
                endpoint = self.config.browser_endpoint

                # If HTTP endpoint, Playwright will fetch the WebSocket URL automatically
                if endpoint.startswith('http://'):
                    # Playwright handles HTTP → WebSocket discovery
                    self.browser = await self.playwright.chromium.connect_over_cdp(
                        endpoint
                    )
                else:
                    # Direct WebSocket connection (backward compatibility)
                    self.browser = await self.playwright.chromium.connect_over_cdp(
                        endpoint
                    )

                self._is_launched = True
                logger.info("✅ Connected to existing browser for demo")
                return self.browser
            except Exception as e:
                logger.warning(f"Failed to connect to existing browser: {e}")
                logger.info("Falling back to launching new browser...")

        # Normal launch path
        logger.info(f"Launching Playwright browser (type={self.config.browser_type})")

        # Select browser type
        if self.config.browser_type == "firefox":
            browser_engine = self.playwright.firefox
        elif self.config.browser_type == "webkit":
            browser_engine = self.playwright.webkit
        else:  # default to chromium
            browser_engine = self.playwright.chromium

        self.browser = await browser_engine.launch(
            headless=self.config.headless,
            slow_mo=self.config.slow_mo,
            args=self.config.browser_args if self.config.browser_type == "chromium" else []
        )

        self._is_launched = True
        logger.info(f"Browser launched ({self.config.browser_type}, headless={self.config.headless})")

        return self.browser
    
    async def new_page(self) -> Page:
        """
        Create a new browser page or reuse existing one (demo mode).

        Returns:
            Page instance
        """
        if not self._is_launched:
            await self.launch()

        # In demo mode (connected to existing browser), reuse the existing page
        if self.config.browser_endpoint:
            # Get the existing page instead of creating a new one
            pages = self.browser.contexts[0].pages if self.browser.contexts else []
            if pages:
                self.page = pages[0]
                logger.info(f"📐 Reusing existing browser page (demo mode)")

                # Set viewport to ensure consistency
                await self.page.set_viewport_size(self.config.viewport_size)

                # Set default timeouts
                self.page.set_default_navigation_timeout(self.config.navigation_timeout)
                self.page.set_default_timeout(self.config.element_timeout)

                return self.page

        # Normal mode: create a new page
        self.page = await self.browser.new_page(
            viewport=self.config.viewport_size
        )

        # Set default timeouts
        self.page.set_default_navigation_timeout(self.config.navigation_timeout)
        self.page.set_default_timeout(self.config.element_timeout)

        # Log viewport dimensions
        viewport = self.config.viewport_size
        logger.info(f"📐 Browser page created with viewport: {viewport['width']}x{viewport['height']}px")
        return self.page
    
    async def navigate(self, url: str) -> Tuple[bool, Optional[str]]:
        """
        Navigate to a URL and wait for page load.
        
        Args:
            url: URL to navigate to
            
        Returns:
            Tuple of (success, error_message)
        """
        if not self.page:
            await self.new_page()
        
        try:
            logger.info(f"Navigating to: {url}")
            await self.page.goto(url, wait_until='domcontentloaded')

            log_browser_action('navigate', url, success=True, logger=logger)
            return (True, None)
            
        except Exception as e:
            error_msg = f"Navigation failed: {str(e)}"
            logger.error(error_msg)
            log_browser_action('navigate', url, success=False, logger=logger)
            return (False, error_msg)
    
    async def click_element(
        self,
        selector: str,
        selector_type: SelectorType = SelectorType.AUTO,
        use_javascript: bool = False
    ) -> Tuple[bool, Optional[str]]:
        """
        Click an element on the page.
        
        Implements Pattern 1: Hidden elements need JavaScript click
        Implements Pattern 5: Click by various selector types
        
        Args:
            selector: Element selector
            selector_type: Type of selector (text, id, css, auto)
            use_javascript: Force JavaScript click for hidden elements
            
        Returns:
            Tuple of (success, error_message)
        """
        if not self.page:
            return (False, "No active page")
        
        try:
            # Build locator based on selector type
            if selector_type == SelectorType.TEXT:
                locator = self.page.locator(f'text={selector}')
            elif selector_type == SelectorType.ID:
                if not selector.startswith('#'):
                    selector = f'#{selector}'
                locator = self.page.locator(selector)
            elif selector_type == SelectorType.CSS:
                locator = self.page.locator(selector)
            else:  # AUTO - try to detect
                locator = self.page.locator(selector)
            
            # Try normal click first
            if not use_javascript:
                try:
                    await locator.first.click(timeout=5000)
                    log_browser_action('click', selector, success=True, logger=logger)
                    return (True, None)
                except Exception:
                    # Fall through to JavaScript click
                    pass
            
            # Use JavaScript click for hidden elements
            logger.debug(f"Using JavaScript click for: {selector}")
            
            # Extract ID for JavaScript
            if selector.startswith('#'):
                element_id = selector[1:]
                await self.page.evaluate(f'document.getElementById("{element_id}").click()')
            else:
                await self.page.evaluate(f'document.querySelector("{selector}").click()')
            
            log_browser_action('javascript_click', selector, success=True, logger=logger)
            return (True, None)
            
        except Exception as e:
            error_msg = f"Click failed on {selector}: {str(e)}"
            logger.error(error_msg)
            log_browser_action('click', selector, success=False, logger=logger)
            return (False, error_msg)
    
    async def fill_field(
        self,
        selector: str,
        value: str,
        interaction: InteractionType = InteractionType.FILL
    ) -> Tuple[bool, Optional[str]]:
        """
        Fill a form field with a value.
        
        Implements Pattern 2: Typeahead fields need fill + Enter
        Implements Pattern 4: Number inputs use fill, not select
        
        Args:
            selector: Field selector
            value: Value to fill
            interaction: Interaction type (fill, fill_enter, etc.)
            
        Returns:
            Tuple of (success, error_message)
        """
        if not self.page:
            return (False, "No active page")
        
        try:
            locator = self.page.locator(selector)
            
            if interaction == InteractionType.FILL:
                # Standard fill
                await locator.fill(value)
                log_browser_action('fill', selector, success=True, logger=logger)
                
            elif interaction == InteractionType.FILL_ENTER:
                # Fill + press Enter for typeahead fields
                await locator.fill(value)
                await asyncio.sleep(0.5)  # Wait for suggestions
                await self.page.keyboard.press('Enter')
                log_browser_action('fill_enter', selector, success=True, logger=logger)
                
            elif interaction == InteractionType.SELECT:
                # Select from dropdown
                await locator.select_option(value)
                log_browser_action('select', selector, success=True, logger=logger)
                
            elif interaction == InteractionType.JAVASCRIPT_CLICK:
                # For radio/checkbox that are hidden
                return await self.click_element(selector, use_javascript=True)
            
            return (True, None)
            
        except Exception as e:
            error_msg = f"Fill failed on {selector}: {str(e)}"
            logger.error(error_msg)
            log_browser_action('fill', selector, success=False, logger=logger)
            return (False, error_msg)
    
    async def wait_for_element(
        self,
        selector: str,
        state: str = 'visible',
        timeout: Optional[int] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Wait for an element to reach a specific state.
        
        Implements Pattern 3: Wait for state='attached' for hidden elements
        
        Args:
            selector: Element selector
            state: State to wait for ('attached', 'visible', 'hidden')
            timeout: Timeout in milliseconds (uses config default if None)
            
        Returns:
            Tuple of (success, error_message)
        """
        if not self.page:
            return (False, "No active page")
        
        timeout = timeout or self.config.element_timeout
        
        try:
            await self.page.wait_for_selector(
                selector,
                state=state,
                timeout=timeout
            )
            logger.debug(f"Element found: {selector} (state={state})")
            return (True, None)
            
        except PlaywrightTimeoutError:
            error_msg = f"Timeout waiting for {selector} (state={state})"
            logger.warning(error_msg)
            return (False, error_msg)
        except Exception as e:
            error_msg = f"Wait failed for {selector}: {str(e)}"
            logger.error(error_msg)
            return (False, error_msg)
    
    async def capture_screenshot(
        self,
        full_page: bool = False,  # Use viewport, no resizing
        optimize: bool = True,
        save_to_disk: bool = None,
        filename: str = None,
        apply_zoom: bool = True  # Intelligently zoom to fit more content
    ) -> Tuple[str, int, str]:
        """
        Capture screenshot and return as base64.

        Implements Pattern 6: Viewport screenshots with aggressive zoom
        Implements Pattern 7: Fixed window size (demo-friendly!)

        The Demo-Friendly Solution:
        1. Keep viewport fixed at 1000x1000 (window NEVER resizes!)
        2. Zoom out aggressively (20-100%) to fit as much content as possible
        3. Scroll to top
        4. Take viewport screenshot (captures zoomed content in fixed window)
        5. Restore zoom to 100% (page becomes interactive again)

        Why this works for demos:
        - Browser window stays 1000x1000 throughout entire session
        - No window jumping or movement (perfect for screen recording!)
        - Aggressive zoom (down to 20%) fits up to 5000px content in viewport
        - For 2224px FSA form: zooms to ~44%, fits in viewport
        - Result: Good form capture in 30-50KB, zero window movement

        Trade-off: Some very tall forms may not fit entirely in viewport

        Args:
            full_page: Ignored - always uses viewport (no resizing)
            optimize: Optimize image size and quality
            save_to_disk: Whether to save to disk (uses config.save_screenshots if None)
            filename: Custom filename (auto-generated if None)
            apply_zoom: Apply intelligent zoom to fit more content (default True)

        Returns:
            Tuple of (base64_string, size_in_bytes, filename)
        """
        if not self.page:
            raise RuntimeError("No active page for screenshot")

        try:
            # Apply intelligent zoom to fit more content (no viewport resizing!)
            original_zoom = None
            if apply_zoom:
                original_zoom = await self._apply_intelligent_zoom()

                # Scroll to top to ensure we start from beginning
                if original_zoom is not None:
                    await self.page.evaluate('window.scrollTo(0, 0)')
                    await self.page.wait_for_timeout(300)  # Wait for scroll to complete

            # Capture screenshot as bytes
            # Window stays fixed at 1000x1000, we just zoom content to fit
            screenshot_bytes = await self.page.screenshot(
                full_page=full_page,
                type='jpeg',
                quality=self.config.screenshot_quality
            )

            # Restore original zoom if we changed it
            if original_zoom is not None:
                await self.page.evaluate(f'() => {{ document.body.style.zoom = "{original_zoom}%"; }}')
                await self.page.wait_for_timeout(100)  # Brief wait for zoom restoration

            # Optimize if needed
            if optimize and len(screenshot_bytes) > (self.config.screenshot_max_size_kb * 1024):
                screenshot_bytes = await self._optimize_screenshot(screenshot_bytes)

            # Generate filename if not provided
            if filename is None:
                timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")[:-3]
                filename = f"screenshot_{timestamp}.jpg"

            # Save to disk if requested
            if save_to_disk is None:
                save_to_disk = self.config.save_screenshots

            if save_to_disk:
                screenshot_path = self.config.get_screenshot_path(filename)
                screenshot_path.parent.mkdir(parents=True, exist_ok=True)

                with open(screenshot_path, 'wb') as f:
                    f.write(screenshot_bytes)

                logger.debug(f"📸 Screenshot saved: {screenshot_path.name} ({len(screenshot_bytes)} bytes)")

            # Convert to base64
            base64_str = base64.b64encode(screenshot_bytes).decode('utf-8')

            logger.debug(f"Screenshot captured: {len(screenshot_bytes)} bytes")
            return (base64_str, len(screenshot_bytes), filename)

        except Exception as e:
            logger.error(f"Screenshot failed: {e}")
            raise
    
    async def _apply_intelligent_zoom(self) -> Optional[int]:
        """
        Apply intelligent zoom to fit more form content in viewport.

        Follows MDCalc pattern: Measure form height, calculate optimal zoom
        to fit as much as possible while maintaining readability.

        Returns:
            Original zoom level (for restoration), or None if zoom wasn't changed
        """
        try:
            # Measure form content height and viewport
            measurements = await self.page.evaluate('''
                () => {
                    // Find the main form container
                    const form = document.querySelector('form') || document.body;

                    // Get all form fields to find the bottom-most one
                    const fields = Array.from(form.querySelectorAll('input, select, textarea, button, label'));

                    let maxBottom = 0;
                    for (const field of fields) {
                        const rect = field.getBoundingClientRect();
                        // Use pageYOffset to convert viewport coordinates to document coordinates
                        const absoluteBottom = rect.bottom + window.pageYOffset;
                        maxBottom = Math.max(maxBottom, absoluteBottom);
                    }

                    // Also check form container height (use scrollHeight for actual content height)
                    const formScrollHeight = form.scrollHeight;
                    const formTop = form.getBoundingClientRect().top + window.pageYOffset;
                    const formContentHeight = formTop + formScrollHeight;

                    // Also check document body full height
                    const bodyHeight = document.body.scrollHeight;

                    return {
                        contentHeight: Math.max(maxBottom, formContentHeight, bodyHeight),
                        viewportHeight: window.innerHeight,
                        scrollY: window.pageYOffset
                    };
                }
            ''')

            content_height = measurements['contentHeight']
            viewport_height = measurements['viewportHeight']
            scroll_y = measurements['scrollY']

            # Log measurements for debugging (INFO level so it shows in tests)
            logger.info(f"📐 Zoom calculation: content={content_height:.0f}px, viewport={viewport_height}px, scrollY={scroll_y:.0f}px")

            # Calculate optimal zoom to fit content in viewport
            if content_height > viewport_height:
                # Calculate zoom percentage to fit content (no viewport resizing!)
                # Very aggressive zoom to fit as much as possible in fixed 1000x1000 window
                optimal_zoom = int((viewport_height / content_height) * 100)

                # Clamp between 20-100% (very aggressive zoom for demo-friendly fixed window)
                # Lower limit of 20% allows up to 5000px content in 1000px viewport
                optimal_zoom = max(20, min(optimal_zoom, 100))

                # Only apply if we're actually zooming out
                if optimal_zoom < 100:
                    await self.page.evaluate(f'() => {{ document.body.style.zoom = "{optimal_zoom}%"; }}')
                    logger.info(f"🔍 Zoomed to {optimal_zoom}% to fit content ({content_height:.0f}px → {viewport_height}px viewport)")

                    # Wait for zoom to apply
                    await self.page.wait_for_timeout(300)

                    return 100  # Return original zoom level for restoration
                else:
                    logger.info(f"✓ Zoom not needed - content already fits (optimal={optimal_zoom}%)")

            else:
                logger.info(f"✓ Zoom not needed - content fits in viewport")

            return None  # No zoom applied

        except Exception as e:
            logger.warning(f"⚠️ Intelligent zoom calculation failed (non-critical): {e}")
            return None

    async def _optimize_screenshot(self, screenshot_bytes: bytes) -> bytes:
        """
        Optimize screenshot to reduce size.

        Args:
            screenshot_bytes: Original screenshot bytes

        Returns:
            Optimized screenshot bytes
        """
        try:
            # Load image
            image = Image.open(io.BytesIO(screenshot_bytes))

            # Reduce quality if still too large
            output = io.BytesIO()
            quality = self.config.screenshot_quality

            while quality > 20:
                output.seek(0)
                output.truncate()
                image.save(output, format='JPEG', quality=quality, optimize=True)

                if output.tell() <= (self.config.screenshot_max_size_kb * 1024):
                    break

                quality -= 10

            return output.getvalue()

        except Exception as e:
            logger.warning(f"Screenshot optimization failed: {e}, using original")
            return screenshot_bytes
    
    async def extract_html_context(self, max_elements: Optional[int] = None, for_discovery: bool = False) -> Dict[str, List[Dict[str, Any]]]:
        """
        Extract interactive HTML elements from the current page.

        Returns structured information about inputs, selects, textareas, and buttons.

        Args:
            max_elements: Maximum elements per type (uses config default if None)
            for_discovery: If True, filter to only form-relevant elements

        Returns:
            Dictionary with element information
        """
        if not self.page:
            return {}

        max_elements = max_elements or self.config.max_html_elements

        try:
            context = await self.page.evaluate(f"""
            () => {{
                const getElementInfo = (el) => ({{
                    tag: el.tagName.toLowerCase(),
                    type: el.type || null,
                    id: el.id || null,
                    name: el.name || null,
                    visible: el.offsetParent !== null
                }});

                // Filter function for discovery mode - exclude chat, feedback, etc.
                const isFormRelevant = (el) => {{
                    const id = el.id || '';
                    const className = el.className || '';

                    // Exclude chat, feedback, help elements
                    const excludePatterns = [
                        'chat', 'Chat', 'feedback', 'help', 'Help',
                        'minimize', 'Minimize', 'audio', 'Audio',
                        'close', 'Close', 'timeout', 'Timeout'
                    ];

                    for (const pattern of excludePatterns) {{
                        if (id.includes(pattern) || className.includes(pattern)) {{
                            return false;
                        }}
                    }}

                    return true;
                }};

                let inputs = Array.from(document.querySelectorAll('input'));
                let selects = Array.from(document.querySelectorAll('select'));
                let textareas = Array.from(document.querySelectorAll('textarea'));
                let buttons = Array.from(document.querySelectorAll('button, input[type="submit"], input[type="button"]'));

                // Filter for discovery mode
                if ({str(for_discovery).lower()}) {{
                    inputs = inputs.filter(isFormRelevant);
                    selects = selects.filter(isFormRelevant);
                    textareas = textareas.filter(isFormRelevant);
                    buttons = buttons.filter(isFormRelevant);
                }}

                return {{
                    inputs: inputs.slice(0, {max_elements}).map(getElementInfo),
                    selects: selects.slice(0, {max_elements}).map(el => ({{
                        ...getElementInfo(el),
                        options: Array.from(el.options).slice(0, 10).map(opt => opt.text)
                    }})),
                    textareas: textareas.slice(0, {max_elements}).map(getElementInfo),
                    buttons: buttons.slice(0, {max_elements}).map(getElementInfo)
                }};
            }}
            """)

            logger.debug(f"Extracted HTML context: {len(context.get('inputs', []))} inputs, "
                        f"{len(context.get('buttons', []))} buttons")

            return context

        except Exception as e:
            logger.error(f"Failed to extract HTML context: {e}")
            return {}
    
    async def get_current_url(self) -> str:
        """
        Get the current page URL.
        
        Returns:
            Current URL
        """
        if not self.page:
            return ""
        return self.page.url
    
    async def get_page_title(self) -> str:
        """
        Get the current page title.
        
        Returns:
            Page title
        """
        if not self.page:
            return ""
        return await self.page.title()
    
    async def close(self):
        """
        Close browser and clean up resources.
        """
        if self.page:
            await self.page.close()
            self.page = None
        
        if self.browser:
            await self.browser.close()
            self.browser = None
        
        if self.playwright:
            await self.playwright.stop()
            self.playwright = None
        
        self._is_launched = False
        logger.info("Browser closed")
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.launch()
        await self.new_page()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()


class BrowserSession:
    """
    Manages a browser session for discovery.
    
    Maintains browser state across multiple tool calls.
    """
    
    def __init__(self, session_id: str, config: Optional[FederalScoutConfig] = None):
        """
        Initialize browser session.

        Args:
            session_id: Unique session identifier
            config: FederalScout configuration
        """
        self.session_id = session_id
        self.client = PlaywrightClient(config)
        self.created_at = datetime.utcnow()
        self.last_activity = datetime.utcnow()
        self.pages_discovered = []
        
    def update_activity(self):
        """Update last activity timestamp."""
        self.last_activity = datetime.utcnow()
    
    def is_expired(self, timeout_seconds: int) -> bool:
        """
        Check if session has expired.
        
        Args:
            timeout_seconds: Timeout in seconds
            
        Returns:
            True if session is expired
        """
        age = datetime.utcnow() - self.last_activity
        return age.total_seconds() > timeout_seconds
    
    async def close(self):
        """Close the browser session."""
        await self.client.close()
