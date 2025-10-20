"""
Pytest configuration and fixtures for FederalRunner tests.

Provides shared fixtures and configuration for all tests.
Matches FederalScout pattern for test output directories.
"""

import logging
import sys
from pathlib import Path

import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from config import get_test_config, set_config
from logging_config import setup_logging


@pytest.fixture(scope='session', autouse=True)
def test_config():
    """
    Set up test configuration for the entire test session.

    Creates temporary directories for test outputs and configures logging.
    Uses tests/test_output/ for logs and screenshots.
    Uses shared wizards/ directory for wizard data (where FederalScout saves).
    """
    # Set environment variables for test-specific paths BEFORE creating config
    # This ensures get_test_config() creates the config with the right paths
    test_output_dir = Path(__file__).parent / 'test_output'

    import os
    os.environ['FEDERALRUNNER_SCREENSHOT_DIR'] = str(test_output_dir / 'screenshots')

    # Now create config - it will pick up the screenshot_dir from environment
    config = get_test_config(temp_dir=None)

    # Manually override log_dir (it doesn't read from environment)
    # Use model_copy to create a new instance with the updated value
    config = config.model_copy(update={'log_dir': test_output_dir / 'logs'})

    # Create directories
    config._create_directories()

    set_config(config)

    # Verify the global config was actually set correctly
    from config import get_config
    active_config = get_config()
    assert active_config.screenshot_dir == config.screenshot_dir, \
        f"Config not properly set! Expected {config.screenshot_dir}, got {active_config.screenshot_dir}"

    # Set up logging
    log_file = config.get_log_path('test_execution.log')
    setup_logging(level='DEBUG', use_colors=True, log_to_file=True, log_file=str(log_file))

    logger = logging.getLogger('federalrunner.test')
    logger.info("=" * 80)
    logger.info("FederalRunner Test Session Started")
    logger.info("=" * 80)
    logger.info(f"Test output directory: {test_output_dir}")
    logger.info(f"Wizards directory: {config.wizards_dir}")
    logger.info(f"Screenshots directory: {config.screenshot_dir}")
    logger.info(f"Log file: {log_file}")

    yield config

    logger.info("=" * 80)
    logger.info("FederalRunner Test Session Complete")
    logger.info("=" * 80)


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )


def pytest_collection_modifyitems(config, items):
    """Add markers to tests based on their names."""
    for item in items:
        # Mark integration tests
        if "integration" in item.nodeid.lower() or "execute" in item.nodeid.lower():
            item.add_marker(pytest.mark.integration)

        # Mark slow tests (wizard execution tests are slow)
        if "execute_wizard" in item.nodeid.lower() or "headless" in item.nodeid.lower():
            item.add_marker(pytest.mark.slow)
