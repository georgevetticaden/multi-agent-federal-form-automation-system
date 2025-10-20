# Navigation Timeout Fix for Slow FSA Website

## Problem

FederalRunner execution failed with timeout error when loading the FSA website:

```
Page.goto: Timeout 30000ms exceeded.
Call log:
- navigating to "https://studentaid.gov/aid-estimator/estimate/results", waiting until "networkidle"
```

## Analysis from Logs

Looking at the Cloud Run logs, there were **two execution attempts**:

### First Attempt (16:58:43) - ✅ SUCCEEDED
```
2025-10-20 16:58:43 | INFO | Starting atomic execution: fsa-estimator
2025-10-20 16:58:46 | INFO | Browser launched: webkit (headless=True, viewport=1280x1024)
2025-10-20 16:58:46 | INFO | Navigating to: https://studentaid.gov/aid-estimator/estimate/results
...
2025-10-20 16:59:26 | INFO | [OK] EXECUTION SUCCESSFUL
2025-10-20 16:59:26 | INFO | Execution time: 55816ms (55.8 seconds)
2025-10-20 16:59:26 | INFO | Pages completed: 7
2025-10-20 16:59:26 | INFO | Screenshots: 10
```

**Result**: ✅ Completed successfully in 55.8 seconds

### Second Attempt (16:59:38) - ❌ FAILED
```
2025-10-20 16:59:38 | INFO | Starting atomic execution: fsa-estimator
2025-10-20 16:59:39 | INFO | Browser launched: webkit (headless=True, viewport=1280x1024)
2025-10-20 16:59:39 | INFO | Navigating to: https://studentaid.gov/aid-estimator/estimate/results
...
2025-10-20 17:00:09 | ERROR | Execution failed: TimeoutError: Page.goto: Timeout 30000ms exceeded.
```

**Result**: ❌ Timed out after 30 seconds on initial page load

## Root Cause

The navigation timeout was set to **30 seconds**, but:

1. First execution took **55.8 seconds total** (including navigation and all 7 pages)
2. The FSA website can be slow to load, especially under load
3. The initial `Page.goto()` call waits for `networkidle` which can take longer
4. The 30-second timeout is too aggressive for government websites

The first execution succeeded but Claude didn't receive the response properly, so it retried. The second attempt timed out because the FSA website was loading slowly.

## Solution

Increased navigation timeout from 30 seconds to 60 seconds:

### 1. Updated `/mcp-servers/federalrunner-mcp/src/config.py`

**Before:**
```python
navigation_timeout: int = Field(
    default=30000,
    ge=5000,
    le=60000,
    description="Navigation timeout in milliseconds"
)
```

**After:**
```python
navigation_timeout: int = Field(
    default=60000,
    ge=5000,
    le=120000,
    description="Navigation timeout in milliseconds (FSA can be slow)"
)
```

**Changes:**
- Default increased: `30000` → `60000` (30s → 60s)
- Maximum increased: `60000` → `120000` (60s → 120s)
- Added clarification: "FSA can be slow"

### 2. Updated Deployment Script

Added `FEDERALRUNNER_NAVIGATION_TIMEOUT=60000` to environment variables in:
- `/mcp-servers/federalrunner-mcp/scripts/deploy-to-cloud-run.sh` (lines 244 and 300)

**Initial deployment (Step 6):**
```bash
--set-env-vars="FEDERALRUNNER_NAVIGATION_TIMEOUT=60000"
```

**Update deployment (Step 9):**
```bash
--set-env-vars="...,FEDERALRUNNER_NAVIGATION_TIMEOUT=60000,..."
```

## Expected Results After Fix

With 60-second navigation timeout:

1. ✅ Initial page load has enough time (even when FSA is slow)
2. ✅ First execution succeeded in 55.8s, well under 60s
3. ✅ Retry attempts will also have sufficient time
4. ✅ Total execution timeout (60s) still protects against hung processes

## Verification

After redeployment, monitor logs for successful navigation:

```bash
# Watch for successful page loads
gcloud run services logs tail federalrunner-mcp --region us-central1 | grep "Navigating to"

# Check for timeout errors (should be none)
gcloud run services logs tail federalrunner-mcp --region us-central1 | grep "Timeout"

# Verify execution times
gcloud run services logs tail federalrunner-mcp --region us-central1 | grep "Execution time"
```

Expected output:
```
INFO | Navigating to: https://studentaid.gov/aid-estimator/estimate/results
INFO | [OK] EXECUTION SUCCESSFUL
INFO | Execution time: 55816ms
```

## Related Issues

### Why Two Execution Attempts?

The first execution succeeded but Claude showed a timeout error to the user. This suggests:

1. **Network latency**: Response took longer than Claude's client timeout
2. **Response not received**: MCP protocol message didn't reach Claude properly
3. **Automatic retry**: Claude retried the execution, which then hit the navigation timeout

### Why First Succeeded, Second Failed?

- **First attempt (55.8s)**: FSA website was responsive
- **Second attempt (timeout at 30s)**: FSA website was under load or slow to respond
- Government websites can have variable performance

## Testing Strategy

1. ✅ Fix applied to config and deployment script
2. ⏳ Redeploy to Cloud Run (this will rebuild with new timeout)
3. ⏳ Test from Claude.ai with same query
4. ⏳ Verify execution completes in under 60 seconds
5. ⏳ Monitor logs for any timeout errors

## Additional Optimizations (Future)

If timeouts persist, consider:

1. **Increase execution timeout**: From 60s to 90s total
2. **Optimize wait strategy**: Use `domcontentloaded` instead of `networkidle`
3. **Add retry logic**: Automatic retry on navigation timeout (with exponential backoff)
4. **Cache warmup**: Keep browser instances warm to reduce startup time

## Related Files

- `/mcp-servers/federalrunner-mcp/src/config.py` - Navigation timeout configuration
- `/mcp-servers/federalrunner-mcp/scripts/deploy-to-cloud-run.sh` - Deployment environment variables
- `/docs/fixes/docker-webkit-compatibility-fix.md` - Previous Docker fix

## Timeline

- **16:58:43-16:59:26**: First execution succeeded (55.8s)
- **16:59:31**: Claude reports timeout error to user
- **16:59:38-17:00:10**: Second execution fails (30s navigation timeout)
- **17:00:10**: Timeout error logged in Cloud Run

## Next Steps

1. ✅ Config updated (navigation timeout: 30s → 60s)
2. ✅ Deployment script updated (added env var)
3. ⏳ Redeploy to Cloud Run
4. ⏳ Test from Claude.ai
5. ⏳ Verify no timeout errors in logs
