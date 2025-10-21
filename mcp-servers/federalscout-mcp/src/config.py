"""
Configuration management for FederalScout Discovery Agent.

Loads configuration from environment variables with sensible defaults.

Reference: requirements/discovery/DISCOVERY_REQUIREMENTS.md REQ-DISC-012
"""

import os
from pathlib import Path
from typing import Optional
from pydantic import Field, ConfigDict
from pydantic_settings import BaseSettings


class FederalScoutConfig(BaseSettings):
    """Configuration for FederalScout Discovery Agent."""

    # Browser Configuration
    browser_type: str = Field(
        default="webkit",
        description="Browser engine to use: 'chromium', 'firefox', or 'webkit'. WebKit works in headless mode with FSA."
    )

    headless: bool = Field(
        default=False,
        description="Run browser in headless mode. WebKit works headless with FSA, Chromium/Firefox do not."
    )

    slow_mo: int = Field(
        default=500,
        ge=0,
        le=5000,
        description="Slow down browser actions by N milliseconds (for debugging)"
    )

    browser_endpoint: Optional[str] = Field(
        default=None,
        description="HTTP/WebSocket endpoint to connect to existing browser (for demos). Use 'http://localhost:9222' with start_browser_for_demo.py script. If set, connects instead of launching new browser."
    )

    # Session Management
    session_timeout: int = Field(
        default=1800,
        ge=300,
        le=7200,
        description="Session timeout in seconds (default: 30 minutes)"
    )

    # Screenshot Configuration
    screenshot_quality: int = Field(
        default=60,  # Optimal size (~23KB)
        ge=1,
        le=100,
        description="JPEG quality for screenshots (1-100)"
    )

    screenshot_max_size_kb: int = Field(
        default=50,  # Lower target for better MCP response size
        ge=10,
        le=500,
        description="Target maximum screenshot size in KB"
    )

    # Browser Viewport
    viewport_width: int = Field(
        default=1200,  # Half width of green recording area for split-screen
        ge=800,
        le=3840,
        description="Browser viewport width"
    )

    viewport_height: int = Field(
        default=1400,  # Fits within recording window height
        ge=600,
        le=2160,
        description="Browser viewport height"
    )

    # Timeouts (in milliseconds)
    navigation_timeout: int = Field(
        default=30000,
        ge=5000,
        le=60000,
        description="Navigation timeout in milliseconds"
    )

    element_timeout: int = Field(
        default=10000,
        ge=1000,
        le=30000,
        description="Element wait timeout in milliseconds"
    )

    # Paths (environment variables loaded automatically via env_prefix)
    workspace_root: Optional[Path] = Field(
        default=None,
        description="Workspace root directory"
    )

    wizards_dir: Optional[Path] = Field(
        default=None,
        description="Directory to save discovered wizard structures"
    )

    log_dir: Optional[Path] = Field(
        default=None,
        description="Directory for log files"
    )

    # Discovery Settings
    discovery_version: str = Field(
        default="1.0.0",
        description="Version of FederalScout agent"
    )

    max_html_elements: int = Field(
        default=50,
        ge=10,
        le=200,
        description="Maximum number of HTML elements to extract per page"
    )

    # Development/Debug
    save_screenshots: bool = Field(
        default=True,
        description="Save screenshots to disk for debugging"
    )

    screenshot_dir: Optional[Path] = Field(
        default=None,
        description="Directory to save debug screenshots"
    )

    model_config = ConfigDict(
        env_prefix="FEDERALSCOUT_",
        case_sensitive=False,
        env_file=".env",
        env_file_encoding="utf-8"
    )

    def __init__(self, **kwargs):
        """Initialize configuration. Directories created lazily when first accessed."""
        super().__init__(**kwargs)

        # Set default paths if not provided via environment
        if self.workspace_root is None:
            self.workspace_root = Path.cwd()

        if self.wizards_dir is None:
            # SHARED LOCATION: Use root multi-agent-federal-form-automation-system/wizards/ directory
            # Navigate up from mcp-servers/federalscout-mcp/ to multi-agent-federal-form-automation-system/
            project_root = Path(__file__).parent.parent.parent.parent
            self.wizards_dir = project_root / "wizards"

        if self.log_dir is None:
            # Local to FederalScout: mcp-servers/federalscout-mcp/logs/
            self.log_dir = self.workspace_root / "logs"

        if self.screenshot_dir is None:
            # SHARED LOCATION: Use multi-agent-federal-form-automation-system/wizards/screenshots/federal-scout/
            # Navigate up from mcp-servers/federalscout-mcp/ to multi-agent-federal-form-automation-system/
            project_root = Path(__file__).parent.parent.parent.parent
            self.screenshot_dir = project_root / "wizards" / "screenshots" / "federal-scout"

        # DO NOT create directories here - they'll be created lazily when needed
        # This prevents unwanted directory creation during config initialization
        self._log_config()

    def _log_config(self):
        """Log configuration settings for debugging."""
        import logging
        import json
        logger = logging.getLogger(__name__)

        # Convert config to dict, handling Path objects
        config_dict = {}
        for field_name, field_info in self.model_fields.items():
            value = getattr(self, field_name)
            # Convert Path objects to strings for JSON serialization
            if isinstance(value, Path):
                config_dict[field_name] = str(value)
            else:
                config_dict[field_name] = value

        logger.info("=" * 60)
        logger.info("FederalScout Configuration")
        logger.info("=" * 60)
        logger.info(json.dumps(config_dict, indent=2))
        logger.info("=" * 60)

    @property
    def browser_args(self) -> list:
        """
        Get Playwright browser launch arguments (only used for Chromium).

        Returns:
            List of browser arguments
        """
        args = []

        # Standard arguments for Chromium in headless mode
        if self.headless and self.browser_type == "chromium":
            args.extend([
                '--disable-gpu',
                '--no-sandbox',
                '--disable-dev-shm-usage',
                '--disable-setuid-sandbox'
            ])

        return args

    @property
    def viewport_size(self) -> dict:
        """
        Get viewport size as dictionary.

        Returns:
            Dictionary with width and height
        """
        return {
            'width': self.viewport_width,
            'height': self.viewport_height
        }

    def get_wizard_path(self, wizard_id: str) -> Path:
        """
        Get full path for a wizard JSON file.

        Args:
            wizard_id: The wizard identifier (e.g., "fsa-estimator")

        Returns:
            Path to the wizard JSON file
        """
        # Ensure wizards directory exists
        self.wizards_dir.mkdir(parents=True, exist_ok=True)

        if not wizard_id.endswith('.json'):
            wizard_id = f"{wizard_id}.json"

        return self.wizards_dir / wizard_id

    def get_log_path(self, log_name: str = "federalscout.log") -> Path:
        """
        Get full path for a log file.

        Args:
            log_name: Name of the log file

        Returns:
            Path to the log file
        """
        # Ensure log directory exists
        self.log_dir.mkdir(parents=True, exist_ok=True)

        return self.log_dir / log_name

    def get_screenshot_path(self, filename: str) -> Path:
        """
        Get full path for a screenshot file.

        Args:
            filename: Name of the screenshot file

        Returns:
            Path to the screenshot file
        """
        # Ensure screenshot directory exists (only if screenshots are enabled)
        if self.save_screenshots:
            self.screenshot_dir.mkdir(parents=True, exist_ok=True)

        return self.screenshot_dir / filename


# Global configuration instance
_config: Optional[FederalScoutConfig] = None


def get_config() -> FederalScoutConfig:
    """
    Get the global configuration instance.

    Returns:
        FederalScoutConfig instance
    """
    global _config
    if _config is None:
        _config = FederalScoutConfig()
    return _config


def reload_config() -> FederalScoutConfig:
    """
    Reload configuration from environment.

    Returns:
        New FederalScoutConfig instance
    """
    global _config
    _config = FederalScoutConfig()
    return _config


def set_config(config: FederalScoutConfig):
    """
    Set the global configuration instance.

    Args:
        config: FederalScoutConfig instance to set
    """
    global _config
    _config = config


# Convenience functions for common configurations

def get_dev_config() -> FederalScoutConfig:
    """
    Get development configuration (visible browser, slow motion).

    Returns:
        FederalScoutConfig configured for development
    """
    return FederalScoutConfig(
        headless=False,
        slow_mo=1000,
        save_screenshots=True
    )


def get_test_config(temp_dir: Optional[Path] = None) -> FederalScoutConfig:
    """
    Get test configuration.

    Loads settings from .env file first, then allows environment variable overrides.

    Defaults: browser_type=webkit, headless=False (visible browser for debugging)
    Override with environment variables:
      - FEDERALSCOUT_BROWSER_TYPE=webkit|chromium|firefox
      - FEDERALSCOUT_HEADLESS=true (run headless)
      - FEDERALSCOUT_BROWSER_ENDPOINT=http://localhost:9222 (demo mode)
      - FEDERALSCOUT_VIEWPORT_WIDTH=1000 (viewport width)
      - FEDERALSCOUT_VIEWPORT_HEIGHT=1000 (viewport height)

    Args:
        temp_dir: Temporary directory for test files

    Returns:
        FederalScoutConfig configured for testing
    """
    if temp_dir is None:
        temp_dir = Path.cwd() / "test_output"

    # Load .env file if it exists
    from dotenv import load_dotenv
    env_file = Path.cwd() / '.env'
    if env_file.exists():
        load_dotenv(env_file)

    # Check environment variables (from .env or actual environment)
    browser_type = os.getenv('FEDERALSCOUT_BROWSER_TYPE', 'webkit')
    headless_env = os.getenv('FEDERALSCOUT_HEADLESS', 'false').lower()
    headless = headless_env in ('true', '1', 'yes')
    browser_endpoint = os.getenv('FEDERALSCOUT_BROWSER_ENDPOINT', None)
    viewport_width = int(os.getenv('FEDERALSCOUT_VIEWPORT_WIDTH', '1000'))
    viewport_height = int(os.getenv('FEDERALSCOUT_VIEWPORT_HEIGHT', '1000'))

    return FederalScoutConfig(
        browser_type=browser_type,
        headless=headless,  # Default False - visible browser for debugging
        slow_mo=500,  # Slow down to see what's happening
        session_timeout=300,
        browser_endpoint=browser_endpoint,  # Demo mode support
        viewport_width=viewport_width,
        viewport_height=viewport_height,
        wizards_dir=temp_dir / "wizards",
        log_dir=temp_dir / "logs",
        screenshot_dir=temp_dir / "screenshots",
        save_screenshots=True
    )


def get_production_config() -> FederalScoutConfig:
    """
    Get production configuration for Cloud Run deployment.

    IMPORTANT: FSA website blocks headless Chromium and Firefox.
    Solution: Use WebKit browser which works in headless mode.

    Returns:
        FederalScoutConfig configured for production
    """
    return FederalScoutConfig(
        browser_type="webkit",  # WebKit works headless with FSA
        headless=True,          # Run in headless mode
        slow_mo=0,
        save_screenshots=False
    )
