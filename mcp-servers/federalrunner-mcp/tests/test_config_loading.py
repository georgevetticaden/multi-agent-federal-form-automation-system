"""
Test configuration loading from different sources.

Demonstrates that FederalRunnerConfig loads from:
1. Environment variables (highest priority)
2. .env file
3. Default values (lowest priority)
"""

import os
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from config import FederalRunnerConfig, get_test_config, get_production_config


def test_config_loads_from_env_file():
    """Test that config loads from .env file in current directory."""
    # When running from project root, .env file should be loaded
    config = FederalRunnerConfig()
    
    # These should match .env file values
    assert config.browser_type == "chromium"
    assert config.headless == False
    assert config.viewport_width == 1280
    assert config.viewport_height == 1024
    print("✓ Config loaded from .env file")


def test_config_overrides_with_env_vars():
    """Test that environment variables override .env file."""
    # Set environment variable
    os.environ['FEDERALRUNNER_BROWSER_TYPE'] = 'webkit'

    # Create new config (will reload)
    config = FederalRunnerConfig()

    # Should use env var, not .env file
    assert config.browser_type == "webkit"

    # Cleanup
    del os.environ['FEDERALRUNNER_BROWSER_TYPE']
    print("✓ Environment variables override .env file")


def test_config_overrides_with_constructor():
    """Test that constructor arguments override everything."""
    # Even with env vars and .env file, constructor wins
    config = FederalRunnerConfig(
        browser_type="firefox",
        headless=True,
        viewport_width=800
    )
    
    assert config.browser_type == "firefox"
    assert config.headless == True
    assert config.viewport_width == 800
    print("✓ Constructor arguments have highest priority")


def test_test_config_for_two_phase_testing():
    """Test the two-phase testing configuration helpers."""
    # Phase 1: Non-headless with Chromium
    config_phase1 = get_test_config(headless=False, browser_type="chromium")
    assert config_phase1.headless == False
    assert config_phase1.browser_type == "chromium"
    assert config_phase1.slow_mo == 500  # Slowed down for visibility
    print("✓ Phase 1 config: Non-headless Chromium")
    
    # Phase 2: Headless with WebKit
    config_phase2 = get_test_config(headless=True, browser_type="webkit")
    assert config_phase2.headless == True
    assert config_phase2.browser_type == "webkit"
    assert config_phase2.slow_mo == 0  # Full speed for headless
    print("✓ Phase 2 config: Headless WebKit")


def test_production_config_for_cloud_run():
    """Test production configuration for Cloud Run deployment."""
    config = get_production_config()
    
    # Critical production settings
    assert config.browser_type == "webkit"  # FSA compatibility
    assert config.headless == True
    assert config.save_screenshots == False  # Don't save to disk
    assert config.slow_mo == 0
    print("✓ Production config: Headless WebKit for Cloud Run")


if __name__ == "__main__":
    print("\n" + "="*60)
    print("FederalRunner Configuration Loading Tests")
    print("="*60 + "\n")

    test_config_loads_from_env_file()
    test_config_overrides_with_env_vars()
    test_config_overrides_with_constructor()
    test_test_config_for_two_phase_testing()
    test_production_config_for_cloud_run()

    print("\n" + "="*60)
    print("All configuration tests passed! ✓")
    print("="*60 + "\n")

    print("Summary of how config loading works:")
    print("-------------------------------------")
    print("Priority (highest to lowest):")
    print("  1. Constructor arguments (e.g., FederalRunnerConfig(headless=True))")
    print("  2. Environment variables (e.g., FEDERALRUNNER_HEADLESS=true)")
    print("  3. .env file (FEDERALRUNNER_HEADLESS=false)")
    print("  4. Default values (headless=False)\n")

    print("This works for:")
    print("  ✓ Local pytest: Loads .env + test overrides")
    print("  ✓ Local MCP with Claude Desktop: Loads .env from working dir")
    print("  ✓ Cloud Run: Uses environment variables set in Cloud Run")
    print()
