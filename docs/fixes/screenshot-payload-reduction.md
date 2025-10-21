# Screenshot Payload Reduction for Production

## Problem

FederalRunner execution succeeded in Cloud Run (completed all 7 pages in 49.6 seconds), but Claude.ai showed "Tool execution failed" to the user even though the logs confirmed success:

```
2025-10-20 17:22:21 | INFO | [OK] EXECUTION SUCCESSFUL
2025-10-20 17:22:21 | INFO | Wizard: fsa-estimator
2025-10-20 17:22:21 | INFO | Pages completed: 7
2025-10-20 17:22:21 | INFO | Execution time: 49662ms
2025-10-20 17:22:21 | INFO | Screenshots: 10
```

**User Experience**: Claude displayed "Tool execution failed" and retried multiple times, even though the execution succeeded.

## Root Cause Analysis

### The Response Size Problem

The MCP response included **10 base64-encoded JPEG screenshots**:

1. Initial page (~50-100KB)
2. After start action (~50-100KB)
3. Page 1 filled (~50-100KB)
4. Page 2 filled (~50-100KB)
5. Page 3 filled (~50-100KB)
6. Page 4 filled (~50-100KB)
7. Page 5 filled (~50-100KB)
8. Page 6 filled (~50-100KB)
9. Page 7 filled (~50-100KB)
10. Final results (~50-100KB)

**Total payload**: ~500KB - 1MB of base64-encoded screenshots

### Why This Causes Failures

1. **Claude.ai client timeout**: Large responses take time to transmit and process
2. **MCP protocol limits**: May have implicit size limits for JSON-RPC responses
3. **Network latency**: Cloud Run → Claude.ai can timeout on large payloads
4. **JSON parsing overhead**: 1MB base64 strings slow down JSON deserialization

### Evidence from Logs

The execution completed successfully, but the response never reached Claude properly:

```
INFO: 169.254.169.126:63832 - "POST / HTTP/1.1" 200 OK
```

HTTP 200 was returned, but Claude.ai treated it as a failure.

## Solution

**Only include the final screenshot in production (headless mode)** instead of all intermediate screenshots.

### Implementation

Updated `/mcp-servers/federalrunner-mcp/src/playwright_client.py` (lines 168-180):

```python
# For production (headless mode), only include final screenshot to reduce response size
# This prevents timeout issues with Claude.ai's MCP client
response_screenshots = screenshots if not self.config.headless else [final_screenshot]

return {
    'success': True,
    'wizard_id': wizard_structure.wizard_id,
    'results': results,
    'screenshots': response_screenshots,  # Only 1 screenshot in production
    'screenshot_count': len(screenshots),  # Total captured (for logging)
    'pages_completed': pages_completed,
    'execution_time_ms': execution_time_ms,
    'timestamp': time.time()
}
```

### Behavior

#### Success Path

**Local Development (headless=False)**:
- Returns all ~10 screenshots (for debugging)
- `screenshots`: [10 base64 strings]
- `screenshot_count`: 10

**Production (headless=True)**:
- Returns only 1 screenshot (final results)
- `screenshots`: [1 base64 string]
- `screenshot_count`: 10

#### Error Path (Visual Validation Loop)

**CRITICAL**: Error path follows Visual Validation Loop pattern (REQ-EXEC-007)

**Local Development (headless=False)**:
- Returns ALL screenshots including error screenshot
- `screenshots`: [all captures up to error point + error screenshot]
- Enables complete step-by-step debugging

**Production (headless=True)**:
- Returns only 1 screenshot (the error screenshot)
- `screenshots`: [1 base64 string]
- `screenshot_count`: Total captured

**Why Only 1 Screenshot for Errors?**

From test_execution_local.py (test_execute_wizard_runtime_error_with_screenshot):
> "This test validates the same self-correcting pattern used in the MDCalc agent:
> 1. Schema validation passes ✅
> 2. Runtime execution fails ❌ (form shows validation error)
> 3. Error screenshot captured 📸 (visual context of failure)
> 4. Claude Vision analyzes screenshot + error message
> 5. Claude guides user to correct the issue
> 6. Re-execute with corrected data"

Claude needs to SEE the error just like a human would. The error screenshot provides:
- **Error Message**: Visible in the screenshot (the most critical information)
- **Page Context**: Shows which page and field caused the error
- **Minimal Payload**: ~50-100KB, prevents timeout issues

**Originally considered returning 3 screenshots** (context, action, error), but simplified to 1 to:
- Prevent payload timeout issues (experienced in production)
- Maintain consistency: 1 screenshot for both success and error
- The error screenshot itself contains sufficient context for Claude Vision

### Response Size Reduction

#### Success Path
**Before**: ~500KB - 1MB (10 screenshots)
**After**: ~50-100KB (1 screenshot)
**Reduction**: ~80-90% smaller payload

#### Error Path
**Before**: Variable (all screenshots up to error point)
**After**: ~50-100KB (1 screenshot - the error screenshot)
**Reduction**: ~80-90% smaller payload, same as success path

**Example**: Error on page 5 (7 screenshots total)
- Local dev: Returns 7 screenshots (~700KB) - complete debugging
- Production: Returns 1 screenshot (~100KB) - the error screenshot only

## Expected Results After Fix

1. ✅ Execution completes successfully (already working)
2. ✅ Claude.ai receives response within timeout
3. ✅ User sees results instead of "Tool execution failed"
4. ✅ Final screenshot still available for verification
5. ✅ All screenshots captured (visible in logs via `screenshot_count`)

## Alternative Solutions Considered

### 1. Compress screenshots more (REJECTED)
- Lower JPEG quality (60 → 40)
- **Problem**: Still need to send 10 images, quality degradation

### 2. Remove all screenshots (REJECTED)
- No screenshots in response
- **Problem**: No visual verification of results

### 3. Send screenshot URLs instead of base64 (FUTURE)
- Store screenshots in Cloud Storage
- Return URLs in response
- **Problem**: Requires Cloud Storage setup, adds complexity

### 4. Only include final screenshot in production (SELECTED ✅)
- Simple, effective, maintains verification
- Local dev still gets all screenshots for debugging
- Production optimized for speed

## Testing Strategy

1. ✅ Code updated (screenshot payload reduction)
2. ⏳ Redeploy to Cloud Run
3. ⏳ Test from Claude.ai with same query
4. ⏳ Verify Claude.ai shows results instead of "Tool execution failed"
5. ⏳ Check response time (should be faster)

## Verification Commands

After redeployment:

```bash
# Monitor execution logs
gcloud run services logs tail federalrunner-mcp --region us-central1

# Check for successful execution
gcloud run services logs tail federalrunner-mcp --region us-central1 | grep "EXECUTION SUCCESSFUL"

# Verify screenshot count (should show 10 captured, 1 returned)
gcloud run services logs tail federalrunner-mcp --region us-central1 | grep "Screenshots"
```

Expected log output:
```
INFO | [OK] EXECUTION SUCCESSFUL
INFO | Screenshots: 10  # Total captured
INFO | screenshot_count: 10, screenshots array length: 1  # Response payload
```

## Related Issues

### Why Not Remove All Screenshots?

Screenshots serve important purposes:

1. **Verification**: Visual proof execution succeeded
2. **Debugging**: See what the browser actually did
3. **Audit trail**: Evidence for compliance/security
4. **Error diagnosis**: See where execution failed

The final screenshot captures the results page, which is the most critical.

### Why Local Dev Gets All Screenshots?

Local development benefits from all screenshots:

1. **Step-by-step debugging**: See each page filled
2. **Field visibility**: Verify selectors work
3. **Interaction validation**: Confirm clicks/fills happen
4. **Performance**: Local network, no timeout issues

## Performance Impact

### Before Fix
- Response size: ~1MB
- Response time: 50 seconds + network time
- Claude.ai timeout: Yes
- User experience: "Tool execution failed"

### After Fix
- Response size: ~100KB (90% reduction)
- Response time: 50 seconds + faster network time
- Claude.ai timeout: No (expected)
- User experience: Shows results successfully

## Future Enhancements

1. **Configurable screenshot strategy**:
   - `FEDERALRUNNER_SCREENSHOT_STRATEGY=final|all|none`
   - Per-wizard configuration

2. **Cloud Storage integration**:
   - Upload screenshots to Google Cloud Storage
   - Return signed URLs in response
   - Longer retention for audit trails

3. **Progressive screenshots**:
   - Stream screenshots during execution
   - Real-time progress updates
   - Better UX for long-running wizards

## Related Files

- `/mcp-servers/federalrunner-mcp/src/playwright_client.py` - Screenshot payload logic
- `/mcp-servers/federalrunner-mcp/src/config.py` - Headless configuration
- `/docs/fixes/navigation-timeout-fix.md` - Previous timeout fix
- `/docs/fixes/docker-webkit-compatibility-fix.md` - Docker base image fix

## Timeline

- **17:21:32**: Execution started
- **17:22:21**: Execution succeeded (49.6 seconds)
- **17:22:21**: HTTP 200 returned to Claude.ai
- **17:22:21**: Claude.ai shows "Tool execution failed" (response timeout/size issue)

## Next Steps

1. ✅ Code updated (production = 1 screenshot only)
2. ⏳ Redeploy to Cloud Run
3. ⏳ Test from Claude.ai
4. ⏳ Verify user sees results successfully
5. ⏳ Monitor response times and errors
