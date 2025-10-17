#!/bin/bash

# FederalRunner Test Runner
# Quick script to run tests in the recommended order

set -e  # Exit on error

echo "=============================================="
echo "FederalRunner Test Suite"
echo "=============================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Step 1: Unit Tests
echo -e "${BLUE}Step 1: Running Unit Tests (fast)...${NC}"
echo "----------------------------------------------"
pytest tests/test_execution_local.py -k "not slow and not e2e" -v
echo ""

# Step 2: MCP Tool Tests
echo -e "${BLUE}Step 2: Running MCP Tool Tests...${NC}"
echo "----------------------------------------------"
pytest tests/test_execution_local.py::test_federalrunner_list_wizards -v
pytest tests/test_execution_local.py::test_federalrunner_get_wizard_info -v
echo ""

# Step 3: Phase 1 - Non-headless (Visual)
echo -e "${YELLOW}Step 3: Running Phase 1 - Non-Headless Chromium (VISUAL)${NC}"
echo "  Watch the browser execute the FSA wizard!"
echo "----------------------------------------------"
pytest tests/test_execution_local.py::test_playwright_client_atomic_execution_non_headless -v -s
echo ""

# Step 4: Phase 2 - Headless (Production)
echo -e "${BLUE}Step 4: Running Phase 2 - Headless WebKit (PRODUCTION)${NC}"
echo "----------------------------------------------"
pytest tests/test_execution_local.py::test_playwright_client_atomic_execution_headless -v -s
echo ""

# Step 5: End-to-End Tests
echo -e "${BLUE}Step 5: Running End-to-End Tests...${NC}"
echo "----------------------------------------------"
pytest tests/test_execution_local.py -m "e2e" -v -s
echo ""

# Step 6: Error Handling Tests
echo -e "${BLUE}Step 6: Running Error Handling Tests...${NC}"
echo "----------------------------------------------"
pytest tests/test_execution_local.py::test_execute_wizard_validation_failure -v
pytest tests/test_execution_local.py::test_execute_wizard_nonexistent_wizard -v
echo ""

echo -e "${GREEN}=============================================="
echo "✅ All tests completed successfully!"
echo "=============================================${NC}"
echo ""
echo "Next steps:"
echo "  1. Review test output above"
echo "  2. If all pass, proceed to FastAPI MCP Server implementation"
echo "  3. See TEST_INSTRUCTIONS.md for troubleshooting"
