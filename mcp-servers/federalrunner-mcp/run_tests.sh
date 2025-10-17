#!/bin/bash

# FederalRunner Test Runner
# Tests MCP tools that will be exposed via HTTP endpoint

set -e  # Exit on error

echo "=============================================="
echo "FederalRunner MCP Tools Test Suite"
echo "=============================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if .env file exists
if [ ! -f .env ]; then
    echo -e "${RED}ERROR: .env file not found${NC}"
    echo ""
    echo "Please create .env from .env.example:"
    echo "  cp .env.example .env"
    echo ""
    echo "For Phase 1 (Visual Debugging), use:"
    echo "  FEDERALRUNNER_BROWSER_TYPE=chromium"
    echo "  FEDERALRUNNER_HEADLESS=false"
    echo "  FEDERALRUNNER_SLOW_MO=500"
    echo ""
    exit 1
fi

# Step 1: Fast tests (no browser)
echo -e "${BLUE}Step 1: Testing MCP Tools (Fast - No Browser)${NC}"
echo "----------------------------------------------"
echo "Testing: federalrunner_list_wizards()"
pytest tests/test_execution_local.py::test_federalrunner_list_wizards -v
echo ""

echo "Testing: federalrunner_get_wizard_info()"
pytest tests/test_execution_local.py::test_federalrunner_get_wizard_info -v
echo ""

# Step 2: Non-headless execution test (uses .env config)
echo -e "${YELLOW}Step 2: Non-Headless Execution (VISUAL)${NC}"
echo "  Configuration: Uses .env file settings"
echo "    (Recommended: chromium, headless=false, slow_mo=500)"
echo "  Watch the browser execute the FSA wizard!"
echo "----------------------------------------------"
echo "Testing: federalrunner_execute_wizard() [NON-HEADLESS]"
pytest tests/test_execution_local.py::test_federalrunner_execute_wizard_non_headless -v -s
echo ""

# Step 3: Headless execution test (overrides config)
echo -e "${BLUE}Step 3: Headless Execution (PRODUCTION)${NC}"
echo "  Configuration: Test overrides to headless mode"
echo "    (webkit, headless=true, slow_mo=0)"
echo "  Validates production configuration"
echo "----------------------------------------------"
echo "Testing: federalrunner_execute_wizard() [HEADLESS]"
pytest tests/test_execution_local.py::test_federalrunner_execute_wizard_headless -v -s
echo ""

# Step 4: Error Handling Tests
echo -e "${BLUE}Step 4: Error Handling Tests${NC}"
echo "----------------------------------------------"
echo "Testing: Validation failures"
pytest tests/test_execution_local.py::test_execute_wizard_validation_failure -v
echo ""

echo "Testing: Non-existent wizard"
pytest tests/test_execution_local.py::test_execute_wizard_nonexistent_wizard -v
echo ""

echo -e "${GREEN}=============================================="
echo "✅ All tests completed successfully!"
echo "=============================================${NC}"
echo ""
echo "Test Summary:"
echo "  ✅ MCP Tool Tests: 2 passed"
echo "  ✅ Non-headless execution: 1 passed"
echo "  ✅ Headless execution: 1 passed"
echo "  ✅ Error Handling: 2 passed"
echo ""
echo "Total: 6 tests"
echo ""
echo "Next steps:"
echo "  - All tests passed → Ready for FastAPI MCP Server implementation"
echo "  - See docs/execution/TEST_INSTRUCTIONS.md for details"
