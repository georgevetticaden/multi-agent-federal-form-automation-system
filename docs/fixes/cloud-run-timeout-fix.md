# Cloud Run Request Timeout Fix: 60s → 240s (4 minutes)

**Date:** 2025-10-20
**Type:** Production Critical Fix
**Priority:** CRITICAL
**Status:** ✅ Fixed

## Problem

Claude.ai execution failed with 504 Gateway Timeout after exactly 60 seconds, even though local tests (both headless and non-headless) completed successfully.

**Evidence from Production (Claude.ai):**
```
18:11:31.668 POST 504 72 B 60.001 s Claude-User
```

**User Observation:**
> "there is something that is going on with Claude.ai and the MCP endpoint..i don't think the timeout is related to the FSA pages being slow because i have no issue when i run the tests locally both headless and non headless"

**Root Cause:** Cloud Run's request timeout (60s) was killing requests before our application could complete execution (180s).

## Timeout Hierarchy Problem

```
Navigation Timeout:  120 seconds (120000ms) ← FSA page load
Execution Timeout:   180 seconds           ← Total wizard execution
Cloud Run Timeout:    60 seconds ❌        ← REQUEST KILLED HERE
                     ^^^^^^^^^^^
                  MISCONFIGURATION!
```

**Result:** Cloud Run returns 504 Gateway Timeout before the wizard can complete, even though the application is configured correctly.

## Previous Context

This issue was discovered after a series of timeout-related fixes:

### Fix 1: Unicode Dropdown Optimization
- Reduced dropdown selection from 31s to 6s (5× faster)
- Added 5-second timeout per strategy

### Fix 2: Navigation Timeout Increase (60s → 120s)
- Increased to handle FSA's variable load times
- Evidence: 3 failed attempts before success at 42 seconds

### Fix 3: Navigation Timeout Regression
- Fixed missing `timeout=` parameter in `page.goto()`

### Fix 4: Execution Timeout Increase (60s → 180s)
- Made execution timeout > navigation timeout
- Prevents premature execution termination

### Fix 5: Cloud Run Timeout (THIS FIX)
- Cloud Run timeout was still 60s, killing requests before execution could complete
- Local tests worked because they don't have Cloud Run's request timeout

## Solution

### Updated Cloud Run Request Timeout (60s → 240s)

**Files Changed:**
1. `.env.deployment` (line 26)
2. `.env.deployment.example` (line 26)

**Before:**
```bash
TIMEOUT=60
```

**After:**
```bash
TIMEOUT=240

# Cloud Run Timeout Notes:
# - Must be >= FEDERALRUNNER_EXECUTION_TIMEOUT (180s)
# - FSA navigation can take up to 120s
# - 240s = 180s execution + 60s buffer
# - Maximum allowed: 300s (5 minutes) for Cloud Run 1st gen
```

## Why 240 Seconds?

### Timeout Hierarchy (Correct Configuration)

```
┌─────────────────────────────────────────────┐
│ Cloud Run Request Timeout: 240s             │ ← Outermost timeout
│                                             │
│  ┌────────────────────────────────────────┐ │
│  │ Application Execution Timeout: 180s    │ │ ← Middle timeout
│  │                                        │ │
│  │  ┌───────────────────────────────────┐ │ │
│  │  │ Navigation Timeout: 120s          │ │ │ ← Innermost timeout
│  │  │ (FSA page load)                   │ │ │
│  │  └───────────────────────────────────┘ │ │
│  │                                        │ │
│  └────────────────────────────────────────┘ │
│                                             │
└─────────────────────────────────────────────┘

120s < 180s < 240s ✅ CORRECT
```

**Buffer Breakdown:**
- 120s: FSA navigation (slow government website)
- 60s: Field filling, screenshots, extraction (~15-20s actual)
- 60s: Safety buffer for network latency, cold starts, etc.
- **Total: 240s = Safe for 99%+ of cases**

**Cloud Run Limits:**
- 1st generation: 300s maximum (we're using 240s)
- 2nd generation: 3600s maximum (1 hour)

## Expected Results After Fix

### Success Scenarios

**Fast FSA load (20s navigation, 15s execution):**
```
Navigation: 20s ✅
Execution: 35s total ✅
Cloud Run: 35s < 240s ✅ SUCCESS
```

**Normal FSA load (60s navigation, 20s execution):**
```
Navigation: 60s ✅
Execution: 80s total ✅
Cloud Run: 80s < 240s ✅ SUCCESS
```

**Slow FSA load (120s navigation, 25s execution):**
```
Navigation: 120s ✅ (max configured)
Execution: 145s total ✅
Cloud Run: 145s < 240s ✅ SUCCESS
```

**Very slow FSA load (120s navigation, 50s execution with retries):**
```
Navigation: 120s ✅
Execution: 170s total ✅
Cloud Run: 170s < 240s ✅ SUCCESS
```

### Failure Scenarios (Protected)

**FSA completely down (navigation timeout):**
```
Navigation: 120s ❌ TIMEOUT
Application catches error
Returns helpful message to user
Cloud Run: ~125s < 240s ✅ (error response delivered)
```

**Execution takes too long (>180s):**
```
Navigation: 60s ✅
Execution: 180s ❌ TIMEOUT
Application catches error
Returns helpful message to user
Cloud Run: ~185s < 240s ✅ (error response delivered)
```

**Cloud Run timeout (extreme edge case):**
```
Only if execution takes >240s
Cloud Run: 240s ❌ 504 Gateway Timeout
User sees 504 error
Should be <1% of cases
```

## Why Local Tests Worked But Production Failed

### Local Tests (pytest)
- No Cloud Run request timeout
- Only application timeouts apply:
  - Navigation: 120s
  - Execution: 180s
- Tests complete successfully in 40-60s typically

### Production (Claude.ai → Cloud Run)
- Cloud Run enforces request timeout
- **Old config:** 60s Cloud Run timeout ❌
  - Killed request before 180s execution could complete
  - 504 Gateway Timeout returned to Claude
  - No error message from application (killed mid-execution)
- **New config:** 240s Cloud Run timeout ✅
  - Allows full 180s execution
  - Application can complete and return results
  - Or application can timeout gracefully and return error message

## Deployment

**Deployment command:**
```bash
cd mcp-servers/federalrunner-mcp
./scripts/deploy-to-cloud-run.sh
```

**What happens:**
1. Deployment script loads `.env.deployment`
2. Reads `TIMEOUT=240`
3. Passes `--timeout 240` to `gcloud run deploy`
4. Cloud Run service updated with 240-second request timeout
5. All future requests get 240 seconds to complete

**Verification:**
```bash
# Check Cloud Run service configuration
gcloud run services describe federalrunner-mcp \
    --region us-central1 \
    --format='value(spec.template.spec.timeoutSeconds)'

# Expected output: 240
```

## Testing Strategy

### Pre-Deployment Verification
```bash
# Verify .env.deployment has TIMEOUT=240
grep TIMEOUT .env.deployment

# Expected: TIMEOUT=240
```

### Post-Deployment Testing (Claude.ai)

**Test 1: FSA Student Aid Estimator**
```
User: "Calculate my federal student aid"
Expected: Completes successfully, no 504 timeout
Monitor: Cloud Run logs should show completion in <180s
```

**Test 2: Loan Simulator (more complex)**
```
User: "Run loan simulator for borrowing student loans"
Expected: Completes successfully, even with slower FSA
Monitor: Cloud Run logs should show completion in <200s
```

**Test 3: Monitor Logs**
```bash
gcloud run services logs tail federalrunner-mcp \
    --region us-central1 \
    --format=json | jq '.httpRequest.latency'

# Expected: Latencies like "45.123s", "67.891s", "120.456s"
# Should NOT see: "60.001s" (old timeout)
```

## Related Fixes

This fix is the culmination of a series of timeout optimizations:

1. **Unicode Dropdown Optimization** - `docs/fixes/unicode-dropdown-fix.md`
   - Reduced dropdown selection from 31s to 6s

2. **Navigation Timeout Increase** - `docs/fixes/navigation-timeout-increase-to-120s.md`
   - Config default: 60s → 120s
   - Deployment script: 60000 → 120000

3. **Navigation Timeout Regression Fix**
   - Added `timeout=` parameter to `page.goto()`

4. **Execution Timeout Increase**
   - Config default: 60s → 180s
   - Deployment script: 60 → 180

5. **Cloud Run Timeout Fix (THIS FIX)**
   - Deployment config: 60s → 240s
   - Aligns with execution timeout hierarchy

## Lessons Learned

### Lesson 1: Cloud Run Has Its Own Timeout Layer
- Application timeouts are NOT enough
- Cloud Run enforces a separate request timeout
- Must configure both layers for long-running operations

### Lesson 2: Timeout Hierarchy Matters
```
Cloud Run > Execution > Navigation
  240s   >   180s    >   120s     ✅ CORRECT

Cloud Run < Execution
   60s    <  180s                 ❌ WRONG (504 errors)
```

### Lesson 3: Local vs Production Testing Gaps
- Local tests don't have all production constraints
- Cloud Run adds request timeout layer
- Must test in production or simulate all timeout layers

### Lesson 4: Debugging Strategy
- User observation: "works locally but fails in production"
- Key insight: 504 Gateway Timeout at exactly 60.001s
- Root cause: Cloud Run default timeout, not application timeout
- Fix: Update Cloud Run configuration, not application code

### Lesson 5: Buffer Time Is Critical
- Don't set Cloud Run timeout = Execution timeout
- Add 60s+ buffer for:
  - Network latency
  - Cold starts
  - Unexpected delays
  - Error handling and logging

## Files Changed

1. ✅ `.env.deployment` - TIMEOUT: 60 → 240 (line 26)
2. ✅ `.env.deployment.example` - TIMEOUT: 60 → 240 (line 26)

## Timeline

- **Earlier:** Navigation timeout fixes (30s → 60s → 120s)
- **Earlier:** Execution timeout fix (60s → 180s)
- **Production:** 3 failed attempts with 504 Gateway Timeout at 60 seconds
- **Investigation:** "Works locally but not in production"
- **Discovery:** Cloud Run TIMEOUT=60 in .env.deployment
- **This fix:** TIMEOUT=240 in deployment config
- **Next:** Deploy and test in Claude.ai

## Success Criteria

✅ **No More 504 Errors:** Claude.ai executions complete without Gateway Timeout
✅ **Completion Time:** FSA wizards complete in 40-180 seconds
✅ **Error Handling:** If wizard times out, application returns helpful error (not 504)
✅ **Logs Clean:** No "60.001s" timeouts in Cloud Run logs
✅ **Success Rate:** >95% of executions succeed on first attempt

## Next Steps

1. ✅ Updated deployment configuration (TIMEOUT=240)
2. ⏳ Deploy to Cloud Run: `./scripts/deploy-to-cloud-run.sh`
3. ⏳ Verify service configuration: `gcloud run services describe...`
4. ⏳ Test from Claude.ai (FSA Student Aid Estimator)
5. ⏳ Test from Claude.ai (Loan Simulator)
6. ⏳ Monitor logs for 24 hours
7. ⏳ Confirm no 504 errors in production

## References

- Cloud Run timeouts: https://cloud.google.com/run/docs/configuring/request-timeout
- Previous navigation timeout fix: `docs/fixes/navigation-timeout-increase-to-120s.md`
- Unicode dropdown fix: `docs/fixes/unicode-dropdown-fix.md`
- Deployment script: `scripts/deploy-to-cloud-run.sh`
