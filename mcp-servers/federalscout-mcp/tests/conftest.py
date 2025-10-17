"""
Pytest configuration and fixtures for FederalScout tests.

Provides shared fixtures and configuration for all tests.
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
    """
    temp_dir = Path(__file__).parent / 'test_output'
    config = get_test_config(temp_dir)
    set_config(config)
    
    # Set up logging
    log_file = config.get_log_path('test_discovery.log')
    setup_logging(log_file=log_file, level=logging.DEBUG, structured=False)
    
    logger = logging.getLogger('federalscout.test')
    logger.info("=" * 80)
    logger.info("FederalScout Test Session Started")
    logger.info("=" * 80)
    logger.info(f"Test output directory: {temp_dir}")
    logger.info(f"Wizards directory: {config.wizards_dir}")
    logger.info(f"Log file: {log_file}")
    
    yield config
    
    logger.info("=" * 80)
    logger.info("FederalScout Test Session Complete")
    logger.info("=" * 80)


@pytest.fixture
def session_holder():
    """
    Fixture to hold session ID across tests.
    
    Returns a dictionary that can be used to store and retrieve
    the session ID across multiple test methods.
    """
    return {'session_id': None}


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
        if "integration" in item.nodeid.lower() or "full" in item.nodeid.lower():
            item.add_marker(pytest.mark.integration)
        
        # Mark slow tests
        if "full" in item.nodeid.lower() or "complete" in item.nodeid.lower():
            item.add_marker(pytest.mark.slow)
