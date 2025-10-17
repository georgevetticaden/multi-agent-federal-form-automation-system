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


@pytest.fixture(scope='session')
def test_config():
    """
    Set up test configuration for the entire test session.

    Creates temporary directories for test outputs and configures logging.
    Uses tests/test_output/ for logs and screenshots.
    Uses shared wizards/ directory for wizard data (where FederalScout saves).
    """
    # Don't pass temp_dir - let get_test_config() use shared wizards directory
    # We'll manually override log_dir and screenshot_dir for test isolation
    test_output_dir = Path(__file__).parent / 'test_output'

    config = get_test_config(temp_dir=None)

    # Override only log_dir and screenshot_dir to use test_output
    # IMPORTANT: Do this before set_config() so the global config has correct paths
    config.log_dir = test_output_dir / 'logs'
    config.screenshot_dir = test_output_dir / 'screenshots'
    config._create_directories()  # Create the new directories

    set_config(config)

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
