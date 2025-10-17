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
NC='\033[0m' # No Color

# Step 1: Fast tests (no browser)
echo -e "${BLUE}Step 1: Testing MCP Tools (Fast - No Browser)${NC}"
echo "----------------------------------------------"
echo "Testing: federalrunner_list_wizards()"
pytest tests/test_execution_local.py::test_federalrunner_list_wizards -v
echo ""

echo "Testing: federalrunner_get_wizard_info()"
pytest tests/test_execution_local.py::test_federalrunner_get_wizard_info -v
echo ""

# Step 2: Phase 1 - Non-headless (Visual)
echo -e "${YELLOW}Step 2: Phase 1 - Non-Headless Chromium (VISUAL)${NC}"
echo "  Watch the browser execute the FSA wizard!"
echo "----------------------------------------------"
echo "Testing: federalrunner_execute_wizard() [NON-HEADLESS]"
pytest tests/test_execution_local.py::test_federalrunner_execute_wizard_non_headless -v -s
echo ""

# Step 3: Phase 2 - Headless (Production)
echo -e "${BLUE}Step 3: Phase 2 - Headless WebKit (PRODUCTION)${NC}"
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
echo "  ✅ Phase 1 (Non-headless): 1 passed"
echo "  ✅ Phase 2 (Headless): 1 passed"
echo "  ✅ Error Handling: 2 passed"
echo ""
echo "Total: 6 tests"
echo ""
echo "Next steps:"
echo "  - All tests passed → Ready for FastAPI MCP Server implementation"
echo "  - See docs/execution/TEST_INSTRUCTIONS.md for details"
