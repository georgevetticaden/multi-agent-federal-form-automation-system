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
        default=60,
        ge=10,
        le=120,
        description="Maximum execution time for a wizard in seconds"
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
        env_file_encoding="utf-8"
    )

    def __init__(self, **kwargs):
        """Initialize configuration and create necessary directories."""
        super().__init__(**kwargs)

        # Set default paths if not provided via environment
        if self.workspace_root is None:
            self.workspace_root = Path.cwd()

        if self.wizards_dir is None:
            # SHARED LOCATION: Use root multi-agent-federal-form-automation-system/wizards/ directory
            # Navigate up from mcp-servers/federalrunner-mcp/ to multi-agent-federal-form-automation-system/
            project_root = Path(__file__).parent.parent.parent.parent
            self.wizards_dir = project_root / "wizards"

        if self.log_dir is None:
            # Local to FederalRunner: mcp-servers/federalrunner-mcp/logs/
            self.log_dir = self.workspace_root / "logs"

        if self.screenshot_dir is None:
            # Local to FederalRunner: mcp-servers/federalrunner-mcp/screenshots/
            self.screenshot_dir = self.workspace_root / "screenshots"

        self._create_directories()
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


def get_test_config(temp_dir: Optional[Path] = None, headless: bool = False, browser_type: str = "chromium") -> FederalRunnerConfig:
    """
    Get test configuration.

    CRITICAL: Two-phase testing approach:
    1. Non-headless first: browser_type="chromium", headless=False (debugging)
    2. Headless second: browser_type="webkit", headless=True (production validation)

    Args:
        temp_dir: Temporary directory for test files
        headless: Run in headless mode (False for debugging, True for production test)
        browser_type: Browser engine (chromium for non-headless, webkit for headless)

    Returns:
        FederalRunnerConfig configured for testing
    """
    if temp_dir is None:
        temp_dir = Path.cwd() / "test_output"

    return FederalRunnerConfig(
        browser_type=browser_type,
        headless=headless,
        slow_mo=500 if not headless else 0,  # Slow down for visible browser
        execution_timeout=60,
        wizards_dir=temp_dir / "wizards",
        log_dir=temp_dir / "logs",
        screenshot_dir=temp_dir / "screenshots",
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
        execution_timeout=60
    )
