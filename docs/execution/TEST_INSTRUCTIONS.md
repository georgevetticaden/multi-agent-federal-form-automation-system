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

The test suite has **6 tests total** organized into three categories:

| Test Type | Count | Speed | Browser | Purpose |
|-----------|-------|-------|---------|---------|
| **MCP Tool Tests** | 2 | Fast (~1s) | None | Test tools Claude will call |
| **Integration Tests (Browser)** | 2 | Slow (~20-40s each) | Chromium/WebKit | Full wizard execution |
| **Error Handling Tests** | 2 | Fast (~1s) | None | Validation & error cases |

### Test Breakdown

1. `test_federalrunner_list_wizards()` - MCP tool test (fast)
2. `test_federalrunner_get_wizard_info()` - MCP tool test (fast)
3. `test_federalrunner_execute_wizard_non_headless()` - Integration test (slow, visual)
4. `test_federalrunner_execute_wizard_headless()` - Integration test (slow, production)
5. `test_execute_wizard_validation_failure()` - Error handling test (fast)
6. `test_execute_wizard_nonexistent_wizard()` - Error handling test (fast)

---

## Running Tests

### Quick Start: Run All Tests

```bash
# Activate virtual environment
source venv/bin/activate

# Run all 6 tests
pytest tests/test_execution_local.py -v
```

**Total time: ~60-90 seconds** (depending on network speed and browser startup)

---

## Step-by-Step Testing Guide

### Step 1: MCP Tool Tests (Fast - No Browser)

Test the MCP tools that Claude will call:

```bash
pytest tests/test_execution_local.py::test_federalrunner_list_wizards -v
pytest tests/test_execution_local.py::test_federalrunner_get_wizard_info -v
```

**What's tested:**
1. **list_wizards** - Lists available wizards from `wizards/wizard-structures/`
2. **get_wizard_info** - Returns THE SCHEMA (contract) from `wizards/data-schemas/`

**Expected:** Both tests pass in < 2 seconds total, confirming:
- FSA wizard is discoverable
- Schema is accessible and valid JSON Schema (draft-07)
- Schema includes Claude hints and example data

---

### Step 2: Phase 1 Integration Test (NON-HEADLESS) ⭐ VISUAL TEST

**IMPORTANT:** This opens a visible browser window!

```bash
pytest tests/test_execution_local.py::test_federalrunner_execute_wizard_non_headless -v -s
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
🔵 Non-Headless Chromium Execution (Visual Debugging)
   Watch the browser execute the FSA wizard visually
   Configuration loaded from .env file
   Screenshots will be saved to: tests/test_output/screenshots/
======================================================================

🚀 MCP Tool: federalrunner_execute_wizard(wizard_id='fsa-estimator')
   User data fields provided: 17 fields

📋 Step 1: Loading User Data Schema...
   ✓ Schema loaded

✅ Step 2: Validating user data against schema...
   ✓ Validation passed

📂 Step 3: Loading Wizard Structure...
   ✓ Wizard loaded: FSA Student Aid Estimator (7 pages)

🔗 Step 4: Mapping field_id → selector...
   ✓ Mapped 17 fields

🎭 Step 5: Executing wizard with Playwright...
   Browser: chromium, Headless: False, Slow Mo: 500ms

🎭 Starting atomic execution: fsa-estimator
📄 Page 1/7: Student Information
📄 Page 2/7: Student Personal Circumstances
📄 Page 3/7: Parent Marital Status
📄 Page 4/7: Parent Information
📄 Page 5/7: Family Size
📄 Page 6/7: Parent Income and Assets
📄 Page 7/7: Student Income and Assets
📊 Extracting results from final page
✅ Execution completed in ~40000ms

======================================================================
✅ EXECUTION SUCCESSFUL
   Wizard: fsa-estimator
   Pages completed: 7
   Execution time: ~40000ms
   Screenshots: 10
======================================================================

✅ NON-HEADLESS TEST PASSED
======================================================================
```

**Execution time:** ~20-40 seconds (with slow_mo=500ms for visual debugging)

**Why this test matters:**
- Visual confirmation that all fields are filled correctly
- Perfect for debugging selector issues
- Validates the complete contract-first pattern:
  1. Load schema
  2. Validate user data
  3. Map field_id → selector
  4. Execute atomically

**Screenshots:** Saved to `tests/test_output/screenshots/` (10 images)

---

### Step 3: Phase 2 Integration Test (HEADLESS) ⭐ PRODUCTION MODE

**RUN THIS AFTER Phase 1 passes!**

```bash
pytest tests/test_execution_local.py::test_federalrunner_execute_wizard_headless -v -s
```

**What happens:**
- **No visible browser window** (runs headlessly)
- **Uses WebKit browser** (FSA blocks headless Chromium/Firefox)
- **Same 7-page execution** as Phase 1
- **Production configuration** validation

**Expected output:**
```
======================================================================
🌐 Headless WebKit Execution (Production)
   Testing production-ready headless execution
   Screenshots will be saved to: tests/test_output/screenshots/
======================================================================

[Same execution flow as Phase 1, but faster]

======================================================================
✅ HEADLESS TEST PASSED
   Wizard: fsa-estimator
   Execution time: ~25000ms
   Pages completed: 7
   Screenshots: 10
======================================================================
```

**Execution time:** ~15-25 seconds (no slow_mo delay)

**Why this test matters:**
- Validates production configuration (Cloud Run will use this)
- Confirms WebKit headless works with FSA website
- Faster execution than non-headless
- Critical for deployment readiness

---

### Step 4: Error Handling Tests (Fast - No Browser)

Test validation failures and edge cases:

```bash
pytest tests/test_execution_local.py::test_execute_wizard_validation_failure -v
pytest tests/test_execution_local.py::test_execute_wizard_nonexistent_wizard -v
```

**What's tested:**
1. **Validation failure** - Invalid user_data is caught before browser execution
2. **Non-existent wizard** - Helpful error when wizard doesn't exist

**Expected:** Both tests pass, confirming:
- Schema validation prevents bad data from reaching browser
- Error messages are helpful for debugging
- No browser is launched for invalid requests

---

## Alternative Test Commands

### Run by marker:

```bash
# Fast tests only (no browser execution)
pytest tests/test_execution_local.py -m "not slow" -v

# Slow tests only (browser execution - both phases)
pytest tests/test_execution_local.py -m "slow" -v -s
```

### Run specific test:

```bash
# Any specific test by name
pytest tests/test_execution_local.py::test_federalrunner_list_wizards -v
```

### Run with detailed logging:

```bash
# Show all logs (including DEBUG level)
pytest tests/test_execution_local.py -v -s --log-cli-level=DEBUG
```

---

## Test Output Directory

All test artifacts are saved to `tests/test_output/` (gitignored):

```
mcp-servers/federalrunner-mcp/tests/test_output/
├── logs/
│   └── test_execution.log          # Test execution logs with full details
├── screenshots/
│   └── *.jpg                        # Browser screenshots from test runs
└── wizards/                         # Test-specific wizard data (if generated)
    ├── wizard-structures/
    └── data-schemas/
```

**Note:** Production wizard data uses the shared location:
- `multi-agent-federal-form-automation-system/wizards/wizard-structures/`
- `multi-agent-federal-form-automation-system/wizards/data-schemas/`

### Viewing Screenshots

After running browser tests (Phase 1 or Phase 2):

```bash
# List screenshots
ls -la tests/test_output/screenshots/

# View screenshot count
ls tests/test_output/screenshots/*.jpg | wc -l

# Open screenshots directory
open tests/test_output/screenshots/  # macOS
```

Screenshots are captured:
- After start action (entering wizard)
- After filling each of 7 pages
- After final results extraction
- Total: **10 screenshots per execution**

---

## Configuration

Tests use configuration from `.env` file (auto-created by setup.sh):

```bash
# Browser Configuration (used by non-headless test)
FEDERALRUNNER_BROWSER_TYPE=chromium     # For visual debugging
FEDERALRUNNER_HEADLESS=false            # Show browser window
FEDERALRUNNER_SLOW_MO=500               # Slow down to watch (500ms)

# Note: Headless test overrides these to use webkit/headless
```

### Browser Strategy

**CRITICAL:** FSA website blocks headless Chromium and Firefox.

| Test | Browser | Headless | Slow Mo | Purpose |
|------|---------|----------|---------|---------|
| **Phase 1** | Chromium | ❌ False | 500ms | Visual debugging |
| **Phase 2** | WebKit | ✅ True | 0ms | Production validation |

**Production (Cloud Run):** Uses WebKit headless (same as Phase 2)

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

**Check wizard structure too:**
```bash
ls -la ../../wizards/wizard-structures/fsa-estimator.json
```

---

### Browser doesn't open in Phase 1

**Check `.env` configuration:**
```bash
cat .env | grep HEADLESS
# Should show: FEDERALRUNNER_HEADLESS=false
```

**Check Playwright installation:**
```bash
playwright --version

# Reinstall browsers if needed
playwright install chromium webkit
```

---

### Headless test fails but non-headless passes

**Common causes:**
- FSA website may be blocking headless Chromium
- Verify test uses `browser_type="webkit"` (already configured)
- Look at error message for specific selector failures

**Solution:** Phase 2 test already configured correctly with WebKit. If still fails:
- Check logs in `tests/test_output/logs/test_execution.log`
- Check screenshots in `tests/test_output/screenshots/`

---

### Validation errors: "85000 is not of type 'string'"

**Cause:** Test data has numeric values but schema expects strings.

**Solution:** All numeric fields in test data must be strings:
- ✅ Correct: `"parent_income": "85000"`
- ❌ Wrong: `"parent_income": 85000`

**Other validation issues:**
- Date fields must be zero-padded: `"05"` not `"5"`
- Enum values must match exactly: `"unmarried"` not `"single"`
- Required fields must be present: Check `required` array in schema

---

### Test hangs or times out

**Common causes:**
- Network connectivity issues
- FSA website is down
- Browser crashed

**Solution:**
- Check internet connection
- Visit https://studentaid.gov/aid-estimator/ manually
- Check logs in `tests/test_output/logs/test_execution.log`
- Re-run the test

---

### Selectors fail on specific fields

**FSA website may have changed.**

**Steps to fix:**
1. Re-run FederalScout discovery to update wizard structure
2. Compare new selectors with old ones in `wizards/wizard-structures/fsa-estimator.json`
3. Update test data if field_id names changed

---

## Expected Test Results

**✅ All tests passing:**

```
tests/test_execution_local.py::test_federalrunner_list_wizards PASSED
tests/test_execution_local.py::test_federalrunner_get_wizard_info PASSED
tests/test_execution_local.py::test_federalrunner_execute_wizard_non_headless PASSED [~40s]
tests/test_execution_local.py::test_federalrunner_execute_wizard_headless PASSED [~25s]
tests/test_execution_local.py::test_execute_wizard_validation_failure PASSED
tests/test_execution_local.py::test_execute_wizard_nonexistent_wizard PASSED

========== 6 passed in ~70s ==========
```

---

## Next Steps After Tests Pass

1. ✅ **MCP tool tests pass** → Tools are ready for Claude to call
2. ✅ **Phase 1 (non-headless) passes** → Visual confirmation execution works
3. ✅ **Phase 2 (headless) passes** → Production configuration validated
4. ✅ **Error handling tests pass** → Validation working correctly
5. ✅ **All 6 tests pass** → **Ready for FastAPI MCP Server implementation!**

---

## Files Used by Tests

```
multi-agent-federal-form-automation-system/
├── wizards/                                    # Shared wizard data
│   ├── wizard-structures/
│   │   └── fsa-estimator.json                 # Wizard structure (FederalScout output)
│   └── data-schemas/
│       └── fsa-estimator-schema.json          # User Data Schema (THE CONTRACT)
└── mcp-servers/federalrunner-mcp/
    ├── tests/
    │   ├── test_execution_local.py            # 6 tests
    │   ├── conftest.py                        # Test configuration & fixtures
    │   └── test_output/                       # Test artifacts (gitignored)
    │       ├── logs/test_execution.log
    │       └── screenshots/*.jpg
    ├── .env                                   # Configuration (auto-created by setup.sh)
    └── venv/                                  # Virtual environment (created by setup.sh)
```
