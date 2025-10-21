"""
Configuration management for FederalRunner Execution Agent.

Loads configuration from environment variables with sensible defaults.

Reference: requirements/execution/EXECUTION_REQUIREMENTS.md REQ-EXEC-002
"""

import os
from pathlib import Path
from typing import Optional
from pydantic import Field, ConfigDict
from pydantic_settings import BaseSettings


class FederalRunnerConfig(BaseSettings):
    """Configuration for FederalRunner Execution Agent."""

    # Server Configuration (for Cloud Run deployment)
    mcp_server_url: str = Field(
        default="http://localhost:8080",
        description="URL where the MCP server is accessible (local or Cloud Run)"
    )

    port: int = Field(
        default=8080,
        ge=1024,
        le=65535,
        description="Port for HTTP server (Cloud Run uses PORT env var)"
    )

    # Auth0 OAuth 2.1 Configuration
    auth0_domain: str = Field(
        default="",
        description="Auth0 domain (e.g., 'your-tenant.us.auth0.com')"
    )

    auth0_issuer: str = Field(
        default="",
        description="Auth0 issuer URL (MUST end with trailing slash!)"
    )

    auth0_api_audience: str = Field(
        default="",
        description="Auth0 API audience (e.g., Cloud Run URL)"
    )

    # Browser Configuration
    browser_type: str = Field(
        default="chromium",
        description="Browser engine: 'chromium', 'firefox', or 'webkit'. CRITICAL: Use webkit for headless mode with FSA."
    )

    headless: bool = Field(
        default=False,
        description="Run browser in headless mode. Local: False (debugging), Production: True (Cloud Run)"
    )

    slow_mo: int = Field(
        default=0,
        ge=0,
        le=5000,
        description="Slow down browser actions by N milliseconds (for debugging)"
    )

    # Execution Settings
    execution_timeout: int = Field(
        default=240,  # 4 minutes - must be > navigation_timeout (180s)
        ge=10,
        le=300,
        description="Maximum execution time for a wizard in seconds (must be > navigation_timeout)"
    )

    # Screenshot Configuration
    screenshot_quality: int = Field(
        default=80,
        ge=1,
        le=100,
        description="JPEG quality for audit trail screenshots (1-100)"
    )

    screenshot_max_size_kb: int = Field(
        default=100,
        ge=10,
        le=500,
        description="Target maximum screenshot size in KB"
    )

    # Browser Viewport
    viewport_width: int = Field(
        default=1280,
        ge=800,
        le=3840,
        description="Browser viewport width"
    )

    viewport_height: int = Field(
        default=1024,
        ge=600,
        le=2160,
        description="Browser viewport height"
    )

    # Timeouts (in milliseconds)
    # NOTE: FSA navigation uses retry logic (5 attempts × 20s = 100s max)
    # This field is kept for non-FSA use cases
    navigation_timeout: int = Field(
        default=120000,  # 2 minutes for general use
        ge=5000,
        le=180000,
        description="Navigation timeout in milliseconds (NOTE: FSA uses hardcoded 20s × 5 retries in code)"
    )

    element_timeout: int = Field(
        default=10000,
        ge=1000,
        le=30000,
        description="Element wait timeout in milliseconds"
    )

    # Paths
    workspace_root: Optional[Path] = Field(
        default=None,
        description="Workspace root directory"
    )

    wizards_dir: Optional[Path] = Field(
        default=None,
        description="Directory containing wizard JSON files"
    )

    log_dir: Optional[Path] = Field(
        default=None,
        description="Directory for log files"
    )

    # Execution Settings
    execution_version: str = Field(
        default="1.0.0",
        description="Version of FederalRunner agent"
    )

    # Development/Debug
    save_screenshots: bool = Field(
        default=True,
        description="Save execution screenshots to disk for debugging"
    )

    screenshot_dir: Optional[Path] = Field(
        default=None,
        description="Directory to save execution screenshots"
    )

    model_config = ConfigDict(
        env_prefix="FEDERALRUNNER_",
        case_sensitive=False,
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"  # Ignore extra fields like LOG_LEVEL (used for Python logging, not Pydantic)
    )

    def __init__(self, **kwargs):
        """Initialize configuration and create necessary directories."""
        # Handle Cloud Run's PORT environment variable
        if 'port' not in kwargs and os.getenv('PORT'):
            kwargs['port'] = int(os.getenv('PORT'))

        # Handle Auth0 environment variables (can be set with or without FEDERALRUNNER_ prefix)
        if 'auth0_domain' not in kwargs and os.getenv('AUTH0_DOMAIN'):
            kwargs['auth0_domain'] = os.getenv('AUTH0_DOMAIN')
        if 'auth0_issuer' not in kwargs and os.getenv('AUTH0_ISSUER'):
            kwargs['auth0_issuer'] = os.getenv('AUTH0_ISSUER')
        if 'auth0_api_audience' not in kwargs and os.getenv('AUTH0_API_AUDIENCE'):
            kwargs['auth0_api_audience'] = os.getenv('AUTH0_API_AUDIENCE')
        if 'mcp_server_url' not in kwargs and os.getenv('MCP_SERVER_URL'):
            kwargs['mcp_server_url'] = os.getenv('MCP_SERVER_URL')

        super().__init__(**kwargs)

        # Set default paths if not provided via environment
        if self.workspace_root is None:
            self.workspace_root = Path.cwd()

        if self.wizards_dir is None:
            # Two modes:
            # 1. Local: SHARED LOCATION at multi-agent-federal-form-automation-system/wizards/
            #    - FederalScout WRITES wizard-structures and data-schemas
            #    - FederalRunner READS them
            # 2. Cloud Run: Wizards copied into Docker image at /app/wizards/
            #    - Set via FEDERALRUNNER_WIZARDS_DIR=/app/wizards
            #    - Deployment script copies ../../wizards/ -> src/wizards/ before build
            project_root = Path(__file__).parent.parent.parent.parent
            self.wizards_dir = project_root / "wizards"

        if self.log_dir is None:
            # Local to FederalRunner: mcp-servers/federalrunner-mcp/logs/
            self.log_dir = self.workspace_root / "logs"

        if self.screenshot_dir is None:
            # Local to FederalRunner: mcp-servers/federalrunner-mcp/screenshots/
            self.screenshot_dir = self.workspace_root / "screenshots"

        self._create_directories()

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
        logger.info("FederalRunner Configuration")
        logger.info("=" * 60)
        logger.info(json.dumps(config_dict, indent=2))
        logger.info("=" * 60)

    def _create_directories(self):
        """Create necessary directories if they don't exist."""
        self.wizards_dir.mkdir(parents=True, exist_ok=True)
        self.log_dir.mkdir(parents=True, exist_ok=True)

        if self.save_screenshots:
            self.screenshot_dir.mkdir(parents=True, exist_ok=True)

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
            wizard_id: The wizard identifier (e.g., "fsa-student-aid-estimator")

        Returns:
            Path to the wizard JSON file
        """
        if not wizard_id.endswith('.json'):
            wizard_id = f"{wizard_id}.json"

        return self.wizards_dir / wizard_id

    def get_log_path(self, log_name: str = "federalrunner.log") -> Path:
        """
        Get full path for a log file.

        Args:
            log_name: Name of the log file

        Returns:
            Path to the log file
        """
        return self.log_dir / log_name

    def get_screenshot_path(self, filename: str) -> Path:
        """
        Get full path for a screenshot file.

        Args:
            filename: Name of the screenshot file

        Returns:
            Path to the screenshot file
        """
        return self.screenshot_dir / filename


# Global configuration instance
_config: Optional[FederalRunnerConfig] = None


def get_config() -> FederalRunnerConfig:
    """
    Get the global configuration instance.

    Returns:
        FederalRunnerConfig instance
    """
    global _config
    if _config is None:
        _config = FederalRunnerConfig()
    return _config


def reload_config() -> FederalRunnerConfig:
    """
    Reload configuration from environment.

    Returns:
        New FederalRunnerConfig instance
    """
    global _config
    _config = FederalRunnerConfig()
    return _config


def set_config(config: FederalRunnerConfig):
    """
    Set the global configuration instance.

    Args:
        config: FederalRunnerConfig instance to set
    """
    global _config
    _config = config


# Convenience functions for common configurations

def get_dev_config() -> FederalRunnerConfig:
    """
    Get development configuration (visible browser, slow motion).

    Returns:
        FederalRunnerConfig configured for development
    """
    return FederalRunnerConfig(
        browser_type="chromium",  # Chromium for non-headless local dev
        headless=False,
        slow_mo=1000,
        save_screenshots=True
    )


def get_test_config(temp_dir: Optional[Path] = None) -> FederalRunnerConfig:
    """
    Get test configuration.

    Loads settings from .env file first, then allows environment variable overrides.

    CRITICAL: Two-phase testing approach:
    - Phase 1: browser_type=chromium, headless=False (visual debugging)
    - Phase 2: browser_type=webkit, headless=True (production validation)

    Configure via .env file or environment variables:
      - FEDERALRUNNER_BROWSER_TYPE=chromium|firefox|webkit
      - FEDERALRUNNER_HEADLESS=true|false
      - FEDERALRUNNER_SLOW_MO=500 (milliseconds)
      - FEDERALRUNNER_EXECUTION_TIMEOUT=240 (seconds)

    Defaults (if not specified):
      - browser_type=chromium
      - headless=False
      - slow_mo=500 (non-headless) or 0 (headless)
      - execution_timeout=240

    Args:
        temp_dir: Temporary directory for test files (optional, uses shared wizards/ if None)

    Returns:
        FederalRunnerConfig configured for testing with .env + environment overrides

    Example .env for Phase 1 (visual debugging):
        FEDERALRUNNER_BROWSER_TYPE=chromium
        FEDERALRUNNER_HEADLESS=false
        FEDERALRUNNER_SLOW_MO=500

    Example .env for Phase 2 (headless production):
        FEDERALRUNNER_BROWSER_TYPE=webkit
        FEDERALRUNNER_HEADLESS=true
        FEDERALRUNNER_SLOW_MO=0
    """
    # Load .env file if it exists
    from dotenv import load_dotenv
    env_file = Path.cwd() / '.env'
    if env_file.exists():
        load_dotenv(env_file)

    # Check environment variables (from .env or actual environment)
    # These can be overridden at runtime for different test phases
    browser_type = os.getenv('FEDERALRUNNER_BROWSER_TYPE', 'chromium')
    headless_env = os.getenv('FEDERALRUNNER_HEADLESS', 'false').lower()
    headless = headless_env in ('true', '1', 'yes')
    slow_mo = int(os.getenv('FEDERALRUNNER_SLOW_MO', '500' if not headless else '0'))
    execution_timeout = int(os.getenv('FEDERALRUNNER_EXECUTION_TIMEOUT', '240'))

    # Use shared wizards directory if temp_dir not specified
    # This allows tests to use actual wizard data
    if temp_dir is None:
        # Use actual shared wizards directory (same as default config)
        project_root = Path(__file__).parent.parent.parent.parent
        wizards_dir = project_root / "wizards"
        log_dir = Path.cwd() / "logs"
        # Check for screenshot_dir from environment (used by conftest.py)
        screenshot_dir_env = os.getenv('FEDERALRUNNER_SCREENSHOT_DIR')
        screenshot_dir = Path(screenshot_dir_env) if screenshot_dir_env else Path.cwd() / "screenshots"
    else:
        wizards_dir = temp_dir / "wizards"
        log_dir = temp_dir / "logs"
        screenshot_dir = temp_dir / "screenshots"

    return FederalRunnerConfig(
        browser_type=browser_type,
        headless=headless,
        slow_mo=slow_mo,
        execution_timeout=execution_timeout,
        wizards_dir=wizards_dir,
        log_dir=log_dir,
        screenshot_dir=screenshot_dir,
        save_screenshots=True
    )


def get_production_config() -> FederalRunnerConfig:
    """
    Get production configuration for Cloud Run deployment.

    CRITICAL: FSA website blocks headless Chromium and Firefox.
    Solution: Use WebKit browser which works in headless mode.

    Returns:
        FederalRunnerConfig configured for production
    """
    return FederalRunnerConfig(
        browser_type="webkit",  # WebKit works headless with FSA
        headless=True,          # Run in headless mode
        slow_mo=0,
        save_screenshots=False,  # Don't save to disk in production
        execution_timeout=240
    )
