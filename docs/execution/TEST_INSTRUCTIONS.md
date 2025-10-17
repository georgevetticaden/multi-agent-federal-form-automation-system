# FederalRunner Test Instructions

Complete guide for running FederalRunner tests with step-by-step instructions.

---

## Setup (First Time Only)

### Step 1: Run Setup Script

```bash
cd mcp-servers/federalrunner-mcp
./scripts/setup.sh
```

The setup script will:
- ✅ Find Python 3.10+ (tries 3.13, 3.12, 3.11, 3.10)
- ✅ Create virtual environment
- ✅ Install all dependencies (production + test)
- ✅ Install Playwright browsers (WebKit + Chromium)
- ✅ Create `.env` file from `.env.example`

**That's it!** You're ready to run tests.

---

## Test Structure

The test suite has 14 tests organized into layers:

| Test Type | Count | Speed | Browser |
|-----------|-------|-------|---------|
| **Unit Tests** | 6 | Fast (~5s) | None |
| **MCP Tool Tests** | 2 | Fast (~1s) | None |
| **Integration Tests** | 2 | Slow (~15-25s each) | Chromium/WebKit |
| **End-to-End Tests** | 2 | Slow (~15-25s each) | Chromium/WebKit |
| **Error Handling Tests** | 2 | Fast (~1s) | None |

---

## Running Tests

### Quick Start: Run All Tests

```bash
# Activate virtual environment
source venv/bin/activate

# Run automated test runner (recommended)
./run_tests.sh
```

This runs all 14 tests in the recommended order. **Total time: ~90 seconds.**

---

## Step-by-Step Testing Guide

### Step 1: Unit Tests (Fast - No Browser)

Test individual components without browser execution:

```bash
pytest tests/test_execution_local.py -k "not slow and not e2e" -v
```

**Tests 6 components:**
1. Schema loading (loads `fsa-estimator-schema.json`)
2. Schema validation with valid data
3. Schema validation with invalid data
4. Schema validation with missing fields
5. Wizard structure loading (loads `fsa-estimator.json`)
6. Field ID to selector mapping

**Expected:** All 6 tests pass in < 5 seconds.

---

### Step 2: MCP Tool Tests (Fast - No Browser)

Test MCP tools that Claude will call:

```bash
pytest tests/test_execution_local.py::test_federalrunner_list_wizards -v
pytest tests/test_execution_local.py::test_federalrunner_get_wizard_info -v
```

**Expected:** Both tests pass, confirming:
- Wizards are discoverable (`list_wizards`)
- Schemas are accessible (`get_wizard_info` returns THE CONTRACT)

---

### Step 3: Phase 1 Integration Test (NON-HEADLESS) ⭐ VISUAL TEST

**IMPORTANT:** This opens a visible browser window!

```bash
pytest tests/test_execution_local.py::test_playwright_client_atomic_execution_non_headless -v -s
```

**What you'll see:**
1. **Chromium browser opens** (visible window)
2. **Navigates to** studentaid.gov/aid-estimator
3. **Clicks "Start Estimate"** button
4. **Fills all 7 pages** of the FSA wizard automatically:
   - Page 1: Student Information (6 fields)
   - Page 2: Student Personal Circumstances (2 fields)
   - Page 3: Parent Marital Status (1 field)
   - Page 4: Parent Information (2 fields)
   - Page 5: Family Size (1 field)
   - Page 6: Parent Income and Assets (4 fields)
   - Page 7: Student Income and Assets (1 field)
5. **Browser closes** automatically

**Expected output:**
```
======================================================================
🔵 PHASE 1: Non-Headless Chromium Execution
   Watch the browser execute the FSA wizard visually
======================================================================

Mapped 17 fields

======================================================================
✅ PHASE 1 PASSED
   Execution time: 15000-25000ms
   Pages completed: 7/7
   Screenshots captured: 9
======================================================================
```

**Execution time:** ~15-25 seconds

**Why this test matters:**
- Visual confirmation that all fields are filled correctly
- Perfect for debugging selector issues
- Validates the complete atomic execution pattern

---

### Step 4: Phase 2 Integration Test (HEADLESS) ⭐ PRODUCTION MODE

**RUN THIS AFTER Phase 1 passes!**

```bash
pytest tests/test_execution_local.py::test_playwright_client_atomic_execution_headless -v -s
```

**What happens:**
- **No visible browser window** (runs headlessly)
- **Uses WebKit browser** (FSA blocks headless Chromium)
- **Same 7-page execution** as Phase 1
- **Production configuration** validation

**Expected output:**
```
======================================================================
🌐 PHASE 2: Headless WebKit Execution (Production)
   Testing production-ready headless execution
======================================================================

======================================================================
✅ PHASE 2 PASSED
   Execution time: 12000-20000ms
   Pages completed: 7/7
   Screenshots captured: 9
======================================================================
```

**Execution time:** ~12-20 seconds

**Why this test matters:**
- Validates production configuration (Cloud Run uses this)
- Confirms WebKit headless works with FSA website
- Faster execution than non-headless

---

### Step 5: End-to-End Tests (Complete MCP Workflow) ⭐ CONTRACT-FIRST

These tests execute the **complete workflow Claude will use**:

**Non-headless (visual debugging):**
```bash
pytest tests/test_execution_local.py::test_federalrunner_execute_wizard_e2e_non_headless -v -s
```

**Headless (production validation):**
```bash
pytest tests/test_execution_local.py::test_federalrunner_execute_wizard_e2e_headless -v -s
```

**What's different from Steps 3-4:**
- Tests `federalrunner_execute_wizard()` tool (what Claude actually calls)
- **Includes full contract-first pattern:**
  1. Load User Data Schema from `wizards/data-schemas/`
  2. Validate user_data against schema
  3. Load Wizard Structure from `wizards/wizard-structures/`
  4. Map `field_id` → `selector` (THE CRITICAL MAPPING)
  5. Execute atomically with Playwright

**Expected:** Both tests pass with same output as Steps 3-4.

---

### Step 6: Error Handling Tests (Fast - No Browser)

Test validation failures and edge cases:

```bash
pytest tests/test_execution_local.py::test_execute_wizard_validation_failure -v
pytest tests/test_execution_local.py::test_execute_wizard_nonexistent_wizard -v
```

**Expected:** Both tests pass, confirming:
- Invalid user_data is caught before execution
- Non-existent wizards return helpful error messages

---

## Alternative Test Commands

### Run by marker:

```bash
# Unit tests only
pytest tests/test_execution_local.py -m "not slow" -v

# Slow tests only (browser execution)
pytest tests/test_execution_local.py -m "slow" -v -s

# End-to-end tests only
pytest tests/test_execution_local.py -m "e2e" -v -s
```

### Run specific test:

```bash
# Any specific test by name
pytest tests/test_execution_local.py::test_schema_loading -v
```

---

## Troubleshooting

### Setup script fails with "Python 3.10 or higher is required"

**Solution:** Install Python 3.10+ from https://www.python.org/downloads/

---

### Tests fail with "Schema not found"

```bash
# Verify schema exists
ls -la ../../wizards/data-schemas/fsa-estimator-schema.json
```

**If missing:** Re-run FederalScout discovery to generate the schema.

---

### Tests fail with "Wizard structure not found"

```bash
# Verify wizard structure exists
ls -la ../../wizards/wizard-structures/fsa-estimator.json
```

**If missing:** Re-run FederalScout discovery to generate the wizard structure.

---

### Browser doesn't open in Phase 1

```bash
# Check Playwright installation
playwright --version

# Reinstall browsers
playwright install chromium webkit
```

---

### Headless test fails but non-headless passes

**Common causes:**
- FSA website may be blocking headless Chromium
- Verify test uses `browser_type="webkit"` (check test code)
- Look at error message for specific selector failures

**Solution:** Phase 2 should use WebKit (already configured in tests).

---

### Selectors fail on specific fields

**FSA website may have changed.**

**Steps to fix:**
1. Re-run FederalScout discovery to update wizard structure
2. Compare new selectors with old ones in `wizards/wizard-structures/fsa-estimator.json`
3. Update tests if field mappings changed

---

### Test hangs or times out

**Common causes:**
- Network connectivity issues
- FSA website is down
- Browser crashed

**Solution:**
- Check internet connection
- Visit https://studentaid.gov/aid-estimator/ in your browser manually
- Re-run the test
- Check logs in `mcp-servers/federalrunner-mcp/logs/`

---

## Expected Test Results

**✅ All tests passing:**

```
tests/test_execution_local.py::test_schema_loading PASSED
tests/test_execution_local.py::test_schema_validation_valid_data PASSED
tests/test_execution_local.py::test_schema_validation_invalid_data PASSED
tests/test_execution_local.py::test_schema_validation_missing_required_fields PASSED
tests/test_execution_local.py::test_wizard_structure_loading PASSED
tests/test_execution_local.py::test_field_id_to_selector_mapping PASSED
tests/test_execution_local.py::test_federalrunner_list_wizards PASSED
tests/test_execution_local.py::test_federalrunner_get_wizard_info PASSED
tests/test_execution_local.py::test_playwright_client_atomic_execution_non_headless PASSED [~20s]
tests/test_execution_local.py::test_playwright_client_atomic_execution_headless PASSED [~15s]
tests/test_execution_local.py::test_federalrunner_execute_wizard_e2e_non_headless PASSED [~20s]
tests/test_execution_local.py::test_federalrunner_execute_wizard_e2e_headless PASSED [~15s]
tests/test_execution_local.py::test_execute_wizard_validation_failure PASSED
tests/test_execution_local.py::test_execute_wizard_nonexistent_wizard PASSED

========== 14 passed in ~90s ==========
```

---

## Next Steps After Tests Pass

1. ✅ **All unit tests pass** → Core components working
2. ✅ **Phase 1 & 2 integration tests pass** → Playwright execution validated
3. ✅ **End-to-end tests pass** → Contract-first pattern working
4. ✅ **All 14 tests pass** → **Ready for FastAPI MCP Server implementation!**

---

## Files Used by Tests

```
multi-agent-federal-form-automation-system/
├── wizards/
│   ├── wizard-structures/
│   │   └── fsa-estimator.json          # Wizard structure (FederalScout output)
│   └── data-schemas/
│       └── fsa-estimator-schema.json   # User Data Schema (THE CONTRACT)
└── mcp-servers/federalrunner-mcp/
    ├── tests/
    │   ├── test_execution_local.py     # 14 tests
    │   └── run_tests.sh                # Automated test runner
    ├── .env                            # Configuration (auto-created by setup.sh)
    └── venv/                           # Virtual environment (created by setup.sh)
```
