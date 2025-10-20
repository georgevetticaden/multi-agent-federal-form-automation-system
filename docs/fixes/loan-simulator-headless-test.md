# Loan Simulator Headless WebKit Test

**Date:** 2025-10-20
**Type:** Production Validation Test
**Status:** ✅ Ready to Run

## Purpose

Validates Loan Simulator execution with **production configuration**:
- ✅ Headless WebKit (same as Cloud Run)
- ✅ Unicode dropdown optimization (5s timeout)
- ✅ Repeatable field workflow (Add a Loan)
- ✅ All 6 pages with 2 loans added
- ✅ Target execution time: <30 seconds

## Why This Test is Critical

This test validates the **EXACT** configuration that will run on Cloud Run:
1. **WebKit** (not Chromium) - FSA headless compatibility
2. **Headless mode** - No browser window, pure automation
3. **No slow-mo** - Full speed execution
4. **Optimized timeouts** - 5s per dropdown strategy
5. **Complex workflow** - Repeatable fields with Unicode

If this test passes, the same code will work in production.

## Run Commands

### Run just this test (fastest)
```bash
cd mcp-servers/federalrunner-mcp
source venv/bin/activate
pytest tests/test_execution_local.py::test_loan_simulator_execute_wizard_headless -v
```

### Run both Loan Simulator tests (non-headless + headless)
```bash
pytest tests/test_execution_local.py::test_loan_simulator_execute_wizard_non_headless tests/test_execution_local.py::test_loan_simulator_execute_wizard_headless -v
```

### Run all execution tests
```bash
pytest tests/test_execution_local.py -v
```

## Expected Results

### Success Criteria

✅ **Test passes:** `PASSED [100%]`
✅ **Pages completed:** 6/6
✅ **Execution time:** 20-30 seconds
✅ **Screenshots:** 9 (1 per page + initial + start + final)
✅ **Unicode handling:** "Bachelor's degree" selected with 5s timeout
✅ **Repeatable fields:** 2 loans added successfully
✅ **Browser:** WebKit (headless)

### Log Analysis

**Check for:**
1. **5-second timeout** (not 30s):
   ```
   Strategy 'original value' failed: Timeout 5000ms exceeded
   Selected dropdown option using strategy: unicode apostrophe
   ```

2. **Repeatable field success**:
   ```
   Repeatable field: adding 2 item(s)
   Adding item 1/2
   Item 1 saved
   Adding item 2/2
   Item 2 saved
   Completed adding 2 item(s) to current_loans
   ```

3. **WebKit browser**:
   ```
   Using WebKit
   Browser launched: webkit (headless=True, viewport=1280x1024)
   ```

4. **Fast execution**:
   ```
   Execution completed in <30000ms
   ```

## Test Data

**Loan Simulator Test Data** (`LOAN_SIMULATOR_TEST_DATA`):
- Program: Bachelor's degree (4 years)
- Family income: $75,000 - $110,000
- Borrow amount: $30,000
- Expected salary: $55,000
- Current loans: 2 items
  - Direct Subsidized Loan: 6.39%, $10,000
  - Direct PLUS Loan: 8.94%, $40,000

## What This Test Validates

### 1. Unicode Dropdown Optimization (Fix #7)
- ✅ 5-second timeout per strategy (not 30s)
- ✅ "Bachelor's degree" with Unicode apostrophe
- ✅ Fast fallback to Unicode strategy
- ✅ Total dropdown time: ~6 seconds

### 2. Repeatable Field Workflow (Fix #6)
- ✅ Detects `field_type: "group"` + array value
- ✅ Click "Add a Loan" button
- ✅ Fill sub-fields (loan_type, interest_rate, balance)
- ✅ Click "Save" button
- ✅ Repeat for each loan (2 loans)
- ✅ Unicode handling in sub-field dropdowns

### 3. WebKit Headless Compatibility (Fix #1)
- ✅ WebKit launches successfully
- ✅ FSA website loads in headless mode
- ✅ All interactions work without visible browser

### 4. Production Performance
- ✅ No slow-mo delay (full speed)
- ✅ Execution completes <30 seconds
- ✅ Safe for Cloud Run 60s timeout
- ✅ Acceptable for MCP remote endpoint

## Comparison: Non-Headless vs Headless

| Aspect | Non-Headless (Visual Debug) | Headless (Production) |
|--------|----------------------------|----------------------|
| Browser | Chromium | WebKit |
| Visible | Yes | No |
| Slow Mo | 500ms | 0ms |
| Purpose | Debugging, development | Production validation |
| Speed | Slower (47s with slow-mo) | Faster (20-30s) |
| Cloud Run Match | ❌ Different config | ✅ Exact match |

## Troubleshooting

### Test fails with WebKit launch error
**Symptom:** "Browser type 'webkit' not found"
**Solution:** Install WebKit: `playwright install webkit`

### Test fails with Unicode dropdown timeout
**Symptom:** "Timeout 5000ms exceeded" on all 4 strategies
**Solution:** Check if FSA changed dropdown HTML, verify selectors

### Test fails with repeatable field error
**Symptom:** "Could not save item 1 for field 'current_loans'"
**Solution:** Check if FSA changed "Save" button, verify Add workflow

### Execution time >30 seconds
**Symptom:** Test passes but takes 35-40 seconds
**Solution:** Acceptable for local test, may need investigation if >40s

## Next Steps After This Test Passes

1. ✅ Commit all optimizations to git
2. ✅ Deploy to Cloud Run (Phase 5)
3. ✅ Test from Claude.ai with same data
4. ✅ Verify production execution time <30s
5. ✅ Record demo video on mobile

## Related Documentation

- Unicode optimization: `docs/fixes/dropdown-timeout-optimization.md`
- Repeatable fields: `docs/fixes/repeatable-field-fix.md`
- Unicode dropdowns: `docs/fixes/unicode-dropdown-fix.md`
- Docker WebKit setup: `docs/fixes/docker-webkit-compatibility-fix.md`
- All fixes summary: `docs/fixes/DEPLOYMENT_FIXES_SUMMARY.md`

## Test Implementation

**File:** `tests/test_execution_local.py` (lines 395-484)

**Key features:**
- Overrides env vars: webkit, headless=true, slow_mo=0
- Reloads config to apply changes
- Restores original config after test
- Same pattern as `test_federalrunner_execute_wizard_headless`

## Success Story

This test represents the culmination of 7 critical fixes:
1. Docker base image compatibility → WebKit launches
2. Navigation timeout → FSA loads completely
3. Screenshot payload reduction → MCP response fits
4. Unicode dropdown selection → "Bachelor's" works
5. ID selector handling → Start button clicks
6. Repeatable field workflow → Loans added
7. **Dropdown timeout optimization → Fast execution**

When this test passes, we have confidence that production deployment will succeed.
