# FederalRunner Test Instructions

## Prerequisites

```bash
# Navigate to federalrunner-mcp directory
cd mcp-servers/federalrunner-mcp

# Activate virtual environment (if not already activated)
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies (if not already installed)
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium webkit
```

## Test Structure

The test suite is organized into layers:

1. **Unit Tests** - Individual components (schema loading, validation, mapping)
2. **MCP Tool Tests** - Test MCP tools (list_wizards, get_wizard_info)
3. **Integration Tests** - Playwright execution (Phase 1: non-headless, Phase 2: headless)
4. **End-to-End Tests** - Complete workflow (what Claude actually calls)
5. **Error Handling Tests** - Validation failures, edge cases

## Running Tests

### Step 1: Run Fast Unit Tests First

These tests validate individual components without browser execution:

```bash
pytest tests/test_execution_local.py::test_schema_loading -v
pytest tests/test_execution_local.py::test_schema_validation_valid_data -v
pytest tests/test_execution_local.py::test_schema_validation_invalid_data -v
pytest tests/test_execution_local.py::test_schema_validation_missing_required_fields -v
pytest tests/test_execution_local.py::test_wizard_structure_loading -v
pytest tests/test_execution_local.py::test_field_id_to_selector_mapping -v
pytest tests/test_execution_local.py -k "not slow and not e2e" -v
```

**Expected:** All unit tests should pass quickly (< 5 seconds total).

---

### Step 2: Run MCP Tool Tests

Test the MCP tools (list_wizards, get_wizard_info):

```bash
pytest tests/test_execution_local.py::test_federalrunner_list_wizards -v
pytest tests/test_execution_local.py::test_federalrunner_get_wizard_info -v
```

**Expected:** Both tests should pass, confirming wizards and schemas are accessible.

---

### Step 3: Run Phase 1 Integration Test (NON-HEADLESS) ⭐ START HERE FOR PLAYWRIGHT

**IMPORTANT:** This opens a visible browser window. You'll watch it fill out the FSA form!

```bash
pytest tests/test_execution_local.py::test_playwright_client_atomic_execution_non_headless -v -s
```

**What to watch:**
1. Browser opens (Chromium, visible)
2. Navigates to studentaid.gov/aid-estimator
3. Clicks "Start Estimate" button
4. Fills all 7 pages of the FSA wizard:
   - Page 1: Student Information (birthdate, marital status, state, grade level)
   - Page 2: Personal Circumstances
   - Page 3: Parent Marital Status
   - Page 4: Parent Information
   - Page 5: Family Size
   - Page 6: Parent Income and Assets
   - Page 7: Student Income and Assets
5. Browser closes automatically

**Expected output:**
```
======================================================================
🔵 PHASE 1: Non-Headless Chromium Execution
   Watch the browser execute the FSA wizard visually
======================================================================

Mapped 17 fields

======================================================================
✅ PHASE 1 PASSED
   Execution time: ~15000-25000ms
   Pages completed: 7/7
   Screenshots captured: 9
======================================================================
```

**If this test fails:**
- Check if selectors have changed on the FSA website
- Look at error messages for which field/page failed
- Verify wizard structure JSON is up to date

---

### Step 4: Run Phase 2 Integration Test (HEADLESS) ⭐ RUN AFTER PHASE 1 PASSES

**Production mode with WebKit (FSA-compatible in headless):**

```bash
pytest tests/test_execution_local.py::test_playwright_client_atomic_execution_headless -v -s
```

**What happens:**
- Browser runs headlessly (no visible window)
- WebKit browser used (FSA website blocks headless Chromium)
- Same 7-page execution as Phase 1

**Expected output:**
```
======================================================================
🌐 PHASE 2: Headless WebKit Execution (Production)
   Testing production-ready headless execution
======================================================================

======================================================================
✅ PHASE 2 PASSED
   Execution time: ~12000-20000ms
   Pages completed: 7/7
   Screenshots captured: 9
======================================================================
```

---

### Step 5: Run End-to-End Tests (Complete MCP Workflow) ⭐ FULL CONTRACT-FIRST PATTERN

These tests execute the complete workflow Claude will use:

**Non-headless (visual):**
```bash
pytest tests/test_execution_local.py::test_federalrunner_execute_wizard_e2e_non_headless -v -s
```

**Headless (production):**
```bash
pytest tests/test_execution_local.py::test_federalrunner_execute_wizard_e2e_headless -v -s
```

**What's different:**
- Tests the `federalrunner_execute_wizard()` tool (what Claude actually calls)
- Includes schema loading + validation + mapping + execution
- Full contract-first pattern validation

---

### Step 6: Run Error Handling Tests

Test validation failures and edge cases:

```bash
pytest tests/test_execution_local.py::test_execute_wizard_validation_failure -v
pytest tests/test_execution_local.py::test_execute_wizard_nonexistent_wizard -v
```

**Expected:** Both tests should pass, confirming errors are handled gracefully.

---

## Run All Tests (Complete Suite)

### Fast tests only (no browser):
```bash
pytest tests/test_execution_local.py -k "not slow and not e2e" -v
```

### All tests including browser execution:
```bash
pytest tests/test_execution_local.py -v -s
```

### Run with markers:
```bash
# Unit tests only
pytest tests/test_execution_local.py -m "not slow" -v

# Slow tests only (browser execution)
pytest tests/test_execution_local.py -m "slow" -v -s

# End-to-end tests only
pytest tests/test_execution_local.py -m "e2e" -v -s
```

---

## Troubleshooting

### Tests fail with "Schema not found"
```bash
# Verify schema exists
ls -la ../../wizards/data-schemas/fsa-estimator-schema.json

# Check FEDERALRUNNER_WORKSPACE_ROOT is set correctly
echo $FEDERALRUNNER_WORKSPACE_ROOT
```

### Tests fail with "Wizard structure not found"
```bash
# Verify wizard structure exists
ls -la ../../wizards/wizard-structures/fsa-estimator.json
```

### Browser doesn't open in Phase 1
```bash
# Check Playwright is installed
playwright --version

# Reinstall browsers
playwright install chromium webkit
```

### Headless test fails but non-headless passes
- FSA website may be blocking headless Chromium
- Verify test uses WebKit: `browser_type="webkit"`
- Check error message for specific selector failures

### Selectors fail
- FSA website may have changed
- Re-run FederalScout discovery to update wizard structure
- Compare new selectors with old ones in wizard structure JSON

---

## Expected Test Results

**✅ All passing:**
```
test_schema_loading PASSED
test_schema_validation_valid_data PASSED
test_schema_validation_invalid_data PASSED
test_schema_validation_missing_required_fields PASSED
test_wizard_structure_loading PASSED
test_field_id_to_selector_mapping PASSED
test_federalrunner_list_wizards PASSED
test_federalrunner_get_wizard_info PASSED
test_playwright_client_atomic_execution_non_headless PASSED  [~20s]
test_playwright_client_atomic_execution_headless PASSED  [~15s]
test_federalrunner_execute_wizard_e2e_non_headless PASSED  [~20s]
test_federalrunner_execute_wizard_e2e_headless PASSED  [~15s]
test_execute_wizard_validation_failure PASSED
test_execute_wizard_nonexistent_wizard PASSED

========== 14 passed in ~90s ==========
```

---

## Next Steps After Tests Pass

1. ✅ Phase 1 & 2 integration tests pass → Proceed to FastAPI MCP Server
2. ✅ End-to-end tests pass → Ready for Claude Desktop integration
3. ✅ All tests pass → Ready for Cloud Run deployment planning
