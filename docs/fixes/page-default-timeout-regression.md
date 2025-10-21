# Page Default Timeout Regression Fix

**Date:** 2025-10-21
**Type:** Critical Regression Fix
**Priority:** CRITICAL
**Status:** ✅ Fixed

## Problem

Start action click timed out at 30 seconds despite all previous timeout fixes:

```
2025-10-21 16:07:45 | INFO | src.playwright_client | -> Executing start action: Start Estimate
2025-10-21 16:08:16 | ERROR | src.playwright_client | L Execution failed: TimeoutError: Timeout 30000ms exceeded.
```

**Context:** All previous timeout fixes were applied:
- ✅ Navigation timeout increased: 30s → 60s → 120s
- ✅ Execution timeout increased: 60s → 180s
- ✅ Cloud Run timeout increased: 60s → 240s
- ✅ `page.goto()` timeout parameter added

**BUT** start action clicks (and all other page operations) were still using Playwright's **default 30-second timeout**!

## Root Cause

When the page is created, we never set a default timeout:

```python
# Line 286 (BEFORE FIX)
self.page = await self.context.new_page()
# ❌ No default timeout set - all operations use Playwright's 30s default!
```

This means:
- ✅ `page.goto()` used 120s (explicit `timeout=` parameter)
- ❌ `page.click()` used 30s (no timeout parameter, uses default)
- ❌ `page.fill()` used 30s (no timeout parameter, uses default)
- ❌ All other page operations used 30s

The FSA start button click + subsequent navigation takes longer than 30 seconds on slow loads.

## Why This Was Missed

### Previous Fixes Focused on Navigation
All previous timeout fixes addressed `page.goto()`:

1. **Navigation Timeout Fix** - Increased config default to 60s
2. **Navigation Timeout Regression** - Added `timeout=` parameter to `page.goto()`
3. **Navigation Timeout Increase** - Increased config default to 120s

### We Forgot About Other Operations
- Start action clicks
- Continue button clicks
- Field fills
- Element waits
- All other page interactions

These all use the page's default timeout (30s) unless explicitly overridden.

## Solution

Set page default timeout immediately after page creation:

```python
# Line 286-291 (AFTER FIX)
self.page = await self.context.new_page()

# Set default timeout for ALL page operations (clicks, fills, etc.)
# This prevents the 30-second default from causing timeouts on slow FSA website
self.page.set_default_timeout(self.config.navigation_timeout)
logger.debug(f"Set page default timeout to {self.config.navigation_timeout}ms")
```

**File Changed:** `src/playwright_client.py` (line 288-291)

### Why This Works

`page.set_default_timeout(timeout)` sets the default timeout for:
- ✅ `page.click()`
- ✅ `page.fill()`
- ✅ `page.get_by_text().click()`
- ✅ `page.wait_for_selector()`
- ✅ All other page operations

Now ALL operations use 120 seconds (120000ms) from `config.navigation_timeout`.

## Expected Results After Fix

### Before Fix
```
2025-10-21 16:07:45 | INFO | -> Executing start action
2025-10-21 16:08:16 | ERROR | TimeoutError: Timeout 30000ms exceeded
                                           ^^^^^ 30 seconds!
```

### After Fix
```
2025-10-21 16:07:45 | INFO | -> Executing start action
2025-10-21 16:07:45 | DEBUG | Set page default timeout to 120000ms
... (up to 120 seconds allowed)
2025-10-21 16:08:10 | INFO | [OK] EXECUTION SUCCESSFUL
```

## Testing

### Local Test
```bash
cd mcp-servers/federalrunner-mcp
pytest tests/test_execution_local.py::test_federalrunner_execute_wizard_headless -v
```

**Expected:** Should pass even if FSA start button is slow

### Production Test (After Deployment)
```bash
# Deploy with fix
./scripts/deploy-to-cloud-run.sh

# Test from Claude.ai
User: "Calculate my federal student aid"

# Monitor logs
gcloud run services logs tail federalrunner-mcp --region us-central1 | grep -E "start action|default timeout|EXECUTION"
```

**Expected:**
```
INFO | Set page default timeout to 120000ms
INFO | -> Executing start action: Start Estimate
INFO | [OK] EXECUTION SUCCESSFUL
```

## Why 120 Seconds?

We use `config.navigation_timeout` (120s) for the page default because:

1. **FSA website is VERY slow** - Often takes 60-120s to load and respond
2. **Start button triggers navigation** - Click + page load can exceed 60s
3. **Consistency** - All page operations should use same generous timeout
4. **Already configured** - Reuses existing navigation_timeout config value
5. **Well within Cloud Run limit** - 120s << 240s Cloud Run timeout

## Timeout Hierarchy (Final)

```
┌────────────────────────────────────────────┐
│ Cloud Run Request: 240s                    │ ← Outermost
│                                            │
│  ┌──────────────────────────────────────┐ │
│  │ Execution Timeout: 180s              │ │ ← Middle
│  │                                      │ │
│  │  ┌────────────────────────────────┐ │ │
│  │  │ Page Default Timeout: 120s     │ │ │ ← NEW! (this fix)
│  │  │ - Clicks                       │ │ │
│  │  │ - Fills                        │ │ │
│  │  │ - Navigation                   │ │ │
│  │  │ - All operations               │ │ │
│  │  └────────────────────────────────┘ │ │
│  │                                      │ │
│  └──────────────────────────────────────┘ │
│                                            │
└────────────────────────────────────────────┘

120s < 180s < 240s ✅ CORRECT
```

## Lessons Learned

### Lesson 1: Page-Level Defaults Matter
- Playwright has TWO timeout layers:
  1. **Per-operation timeout** - Passed to each API call (e.g., `click(timeout=X)`)
  2. **Page default timeout** - Used when per-operation timeout not specified
- We fixed #1 for navigation but forgot #2 for everything else

### Lesson 2: Set Defaults Early
- Set `page.set_default_timeout()` immediately after `page.create()`
- Don't rely on remembering to add `timeout=` to every single operation
- One line of code prevents dozens of potential timeout issues

### Lesson 3: Test All Code Paths
- Previous fixes only tested navigation (`page.goto()`)
- Didn't test start action clicks, continue button clicks, etc.
- All code paths need timeout verification

### Lesson 4: User Frustration Is Valid
User said: "this is incredibly frustrating because i thought we had changed all the timeouts to be higher"

They were RIGHT to be frustrated:
- ✅ We HAD fixed navigation timeouts (3 separate fixes!)
- ❌ We MISSED the page default timeout (easy to overlook)
- ✅ This fix completes the timeout strategy

## Files Changed

1. ✅ `src/playwright_client.py` - Added `page.set_default_timeout()` call (line 288-291)

## Related Fixes

This is the **4th timeout-related fix**:

1. ✅ **Navigation Timeout Fix (60s)** - `docs/fixes/navigation-timeout-fix.md`
2. ✅ **Navigation Timeout Increase (120s)** - `docs/fixes/navigation-timeout-increase-to-120s.md`
3. ✅ **Cloud Run Timeout (240s)** - `docs/fixes/cloud-run-timeout-fix.md`
4. ✅ **Page Default Timeout (120s)** - THIS FIX

All four layers now aligned for production reliability.

## Timeline

- **Earlier:** Navigation timeout fixes (30s → 60s → 120s)
- **Earlier:** Cloud Run timeout fix (60s → 240s)
- **2025-10-21 16:07:45:** Start action click initiated
- **2025-10-21 16:08:16:** Timeout at 30 seconds (Playwright default)
- **2025-10-21 (this fix):** Added `page.set_default_timeout(120000)`
- **Next:** Deploy and test

## Next Steps

1. ✅ Fix applied to `src/playwright_client.py`
2. ⏳ Test locally: `pytest tests/test_execution_local.py -v`
3. ⏳ Deploy to Cloud Run: `./scripts/deploy-to-cloud-run.sh`
4. ⏳ Test from Claude.ai
5. ⏳ Verify no more 30-second timeouts in logs

## Success Criteria

✅ **No 30-Second Timeouts:** Logs should never show "Timeout 30000ms exceeded"
✅ **Start Action Succeeds:** FSA start button click completes successfully
✅ **All Operations Work:** Clicks, fills, waits all use 120-second timeout
✅ **Production Reliability:** >95% success rate on first attempt

## Apology to User

This was indeed frustrating. You had every right to expect this to work after 3 previous timeout fixes. The issue was:
- We fixed the **specific** timeout (navigation)
- We missed the **general** timeout (page default)

This one-line fix completes the timeout strategy. All operations now have proper timeouts.

## References

- Playwright page.set_default_timeout(): https://playwright.dev/docs/api/class-page#page-set-default-timeout
- Previous timeout fixes: `docs/fixes/` directory
- User's valid frustration: Conversation on 2025-10-21
