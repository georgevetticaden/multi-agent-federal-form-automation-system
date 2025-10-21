# FederalRunner Timeout Configuration Guide

**Last Updated:** 2025-10-21
**Status:** Production Reference

## Overview

FederalRunner has **4 timeout layers** that must be properly configured for reliable execution of slow government websites (especially FSA, which can take 60-120+ seconds to load).

This document is the **single source of truth** for all timeout configuration.

---

## Timeout Architecture

```
┌──────────────────────────────────────────────────────┐
│ Layer 4: Cloud Run Request Timeout (240s)           │ ← Outermost
│                                                      │
│  ┌────────────────────────────────────────────────┐ │
│  │ Layer 3: Execution Timeout (180s)              │ │
│  │                                                │ │
│  │  ┌──────────────────────────────────────────┐ │ │
│  │  │ Layer 2: Navigation Timeout (120s)       │ │ │
│  │  │                                          │ │ │
│  │  │  ┌────────────────────────────────────┐ │ │ │
│  │  │  │ Layer 1: Page Default (120s)       │ │ │ │
│  │  │  │ - Clicks                          │ │ │ │
│  │  │  │ - Fills                           │ │ │ │
│  │  │  │ - Waits                           │ │ │ │
│  │  │  └────────────────────────────────────┘ │ │ │
│  │  │                                          │ │ │
│  │  └──────────────────────────────────────────┘ │ │
│  │                                                │ │
│  └────────────────────────────────────────────────┘ │
│                                                      │
└──────────────────────────────────────────────────────┘

120s ≤ 120s < 180s < 240s ✅ CORRECT HIERARCHY
```

**Critical Rules:**
1. **Layer 1 ≤ Layer 2** - Page default can equal or be less than navigation timeout
2. **Layer 2 < Layer 3** - Navigation must be less than execution (so execution can handle retries)
3. **Layer 3 < Layer 4** - Execution must be less than Cloud Run (so app can return errors before HTTP timeout)
4. **Add 60s buffer** between each layer for error handling, logging, overhead

---

## Layer 1: Page Default Timeout

### What It Controls
**ALL Playwright page operations** that don't have explicit timeout parameters:
- Button clicks (`page.click()`, `page.get_by_text().click()`)
- Form fills (`page.fill()`, `page.type()`)
- Element waits (`page.wait_for_selector()`)
- Any other page interaction

### Current Value
**120 seconds (120000ms)**

### Why This Value
- FSA buttons/interactions can be very slow (60-90+ seconds)
- Must match or be less than navigation timeout
- Generous enough to handle worst-case FSA slowness
- Still well under execution timeout

### Configuration

#### 1. Source of Truth: Config Default
**File:** `src/config.py` (line ~105)

```python
navigation_timeout: int = Field(
    default=120000,  # 2 minutes
    ge=5000,
    le=180000,
    description="Navigation timeout in milliseconds (FSA website is VERY slow - often >60s)"
)
```

**Note:** Page default timeout uses the `navigation_timeout` config value.

#### 2. Applied in Code
**File:** `src/playwright_client.py` (line ~290)

```python
self.page = await self.context.new_page()

# Set default timeout for ALL page operations
self.page.set_default_timeout(self.config.navigation_timeout)
```

**CRITICAL:** This must be called immediately after `new_page()` to prevent Playwright's 30-second default.

### How to Change

1. **Update config default** in `src/config.py`:
   ```python
   default=150000,  # New value in milliseconds
   ```

2. **No code changes needed** - `playwright_client.py` automatically uses config value

3. **Test locally:**
   ```bash
   pytest tests/test_execution_local.py -v
   ```

4. **Deploy** (config is baked into Docker image):
   ```bash
   ./scripts/deploy-to-cloud-run.sh
   ```

---

## Layer 2: Navigation Timeout

### What It Controls
**Only `page.goto()` operations** - initial page loads and navigation:
- Loading wizard start page
- Navigating between wizard pages
- Waiting for `networkidle` state

### Current Value
**120 seconds (120000ms)**

### Why This Value
- FSA pages often take 60-90+ seconds to load
- Multiple attempts observed at 42s, 67s, 89s
- 120s captures 95%+ of slow loads
- Same as page default for consistency

### Configuration

#### 1. Source of Truth: Config Default
**File:** `src/config.py` (line ~105)

```python
navigation_timeout: int = Field(
    default=120000,  # 2 minutes
    ge=5000,
    le=180000,
    description="Navigation timeout in milliseconds (FSA website is VERY slow - often >60s)"
)
```

#### 2. Applied in Code
**File:** `src/playwright_client.py` (line ~110)

```python
await self.page.goto(
    wizard_structure.url,
    wait_until='networkidle',
    timeout=self.config.navigation_timeout  # Explicit timeout parameter
)
```

**CRITICAL:** The `timeout=` parameter must be explicitly passed. Playwright won't use page default for `goto()`.

#### 3. Deployment Environment Variable
**File:** `scripts/deploy-to-cloud-run.sh` (line ~244, ~300)

```bash
# Initial deployment (line 244)
--set-env-vars="FEDERALRUNNER_NAVIGATION_TIMEOUT=120000"

# Environment update (line 300)
FEDERALRUNNER_NAVIGATION_TIMEOUT=120000
```

### How to Change

1. **Update config default** in `src/config.py`:
   ```python
   default=150000,  # New value
   ```

2. **Update deployment script** in `scripts/deploy-to-cloud-run.sh` (2 places):
   ```bash
   FEDERALRUNNER_NAVIGATION_TIMEOUT=150000
   ```

3. **Verify code** in `src/playwright_client.py` has `timeout=` parameter:
   ```python
   await self.page.goto(..., timeout=self.config.navigation_timeout)
   ```

4. **Update page default too** (should be same value or less)

5. **Test and deploy:**
   ```bash
   pytest tests/test_execution_local.py -v
   ./scripts/deploy-to-cloud-run.sh
   ```

---

## Layer 3: Execution Timeout

### What It Controls
**Total wizard execution time** from browser launch to results extraction:
- Browser startup
- All page navigations
- All field filling
- All screenshots
- Result extraction
- Cleanup

### Current Value
**180 seconds (180s = 3 minutes)**

### Why This Value
- Navigation: up to 120s
- Field filling: ~15-20s
- Screenshots: ~5-10s
- Retries/overhead: ~30s
- Buffer: ~15s
- **Total: 180s safely covers all steps**

### Configuration

#### 1. Source of Truth: Config Default
**File:** `src/config.py` (line ~115)

```python
execution_timeout: int = Field(
    default=180,  # 3 minutes
    ge=30,
    le=300,
    description="Maximum execution time in seconds for wizard completion"
)
```

#### 2. Applied in Code
**File:** `src/playwright_client.py` (line ~95)

```python
async def execute_wizard(self, ...):
    try:
        # Use asyncio.timeout for total execution
        async with asyncio.timeout(self.config.execution_timeout):
            # ... all wizard execution steps ...
    except TimeoutError:
        return error response
```

**Note:** Uses Python's `asyncio.timeout()` context manager.

#### 3. Deployment Environment Variable
**File:** `scripts/deploy-to-cloud-run.sh` (line ~244, ~300)

```bash
# Initial deployment
--set-env-vars="FEDERALRUNNER_EXECUTION_TIMEOUT=180"

# Environment update
FEDERALRUNNER_EXECUTION_TIMEOUT=180
```

### How to Change

1. **Update config default** in `src/config.py`:
   ```python
   default=210,  # New value in SECONDS
   ```

2. **Update deployment script** in `scripts/deploy-to-cloud-run.sh` (2 places):
   ```bash
   FEDERALRUNNER_EXECUTION_TIMEOUT=210
   ```

3. **Ensure hierarchy:** New value must be **greater than navigation timeout**:
   ```
   navigation_timeout (120s) < execution_timeout (210s) ✅
   ```

4. **Test and deploy:**
   ```bash
   pytest tests/test_execution_local.py -v
   ./scripts/deploy-to-cloud-run.sh
   ```

---

## Layer 4: Cloud Run Request Timeout

### What It Controls
**Total HTTP request time** from Claude.ai request to Cloud Run response:
- Cold start time (~5-15s)
- Container initialization
- Full execution timeout (180s)
- Response serialization
- Network latency

### Current Value
**240 seconds (240s = 4 minutes)**

### Why This Value
- Execution: up to 180s
- Cold start: ~10s
- Response overhead: ~10s
- Safety buffer: ~40s
- **Total: 240s with comfortable margin**

**Limit:** 300s maximum for Cloud Run 1st generation (we're at 240s)

### Configuration

#### 1. Source of Truth: Deployment Config
**File:** `.env.deployment` (line ~26)

```bash
TIMEOUT=240

# Cloud Run Timeout Notes:
# - Must be >= FEDERALRUNNER_EXECUTION_TIMEOUT (180s)
# - FSA navigation can take up to 120s
# - 240s = 180s execution + 60s buffer
# - Maximum allowed: 300s (5 minutes) for Cloud Run 1st gen
```

#### 2. Deployment Example File
**File:** `.env.deployment.example` (line ~26)

Same as above - keep in sync with `.env.deployment`.

#### 3. Applied by Deployment Script
**File:** `scripts/deploy-to-cloud-run.sh` (line ~220)

```bash
gcloud run deploy federalrunner-mcp \
    --timeout ${TIMEOUT} \
    ...
```

Reads `TIMEOUT` variable from `.env.deployment` and passes to `gcloud run deploy`.

### How to Change

1. **Update deployment config** in `.env.deployment`:
   ```bash
   TIMEOUT=270
   ```

2. **Update example file** in `.env.deployment.example`:
   ```bash
   TIMEOUT=270
   ```

3. **Ensure hierarchy:** New value must be **greater than execution timeout**:
   ```
   execution_timeout (180s) < Cloud Run timeout (270s) ✅
   ```

4. **Respect limit:** Must be ≤ 300s for Cloud Run 1st gen

5. **Deploy** (deployment script reads .env.deployment):
   ```bash
   ./scripts/deploy-to-cloud-run.sh
   ```

6. **Verify deployment:**
   ```bash
   gcloud run services describe federalrunner-mcp \
       --region us-central1 \
       --format='value(spec.template.spec.timeoutSeconds)'

   # Expected: 270
   ```

---

## Quick Reference: All Values

| Layer | Name | Value | Unit | File(s) |
|-------|------|-------|------|---------|
| 1 | Page Default | 120000 | ms | `src/config.py`, `src/playwright_client.py` |
| 2 | Navigation | 120000 | ms | `src/config.py`, `scripts/deploy-to-cloud-run.sh` |
| 3 | Execution | 180 | seconds | `src/config.py`, `scripts/deploy-to-cloud-run.sh` |
| 4 | Cloud Run | 240 | seconds | `.env.deployment`, `.env.deployment.example` |

**Hierarchy:** `120s ≤ 120s < 180s < 240s` ✅

---

## Common Scenarios

### Scenario 1: FSA is getting slower, increase all timeouts

**Goal:** Increase to handle 150-second FSA loads

**Changes:**
1. **Page Default + Navigation:** 120s → 150s
   - `src/config.py`: `default=150000`
   - `scripts/deploy-to-cloud-run.sh`: `FEDERALRUNNER_NAVIGATION_TIMEOUT=150000`

2. **Execution:** 180s → 210s (150s + 60s buffer)
   - `src/config.py`: `default=210`
   - `scripts/deploy-to-cloud-run.sh`: `FEDERALRUNNER_EXECUTION_TIMEOUT=210`

3. **Cloud Run:** 240s → 270s (210s + 60s buffer)
   - `.env.deployment`: `TIMEOUT=270`
   - `.env.deployment.example`: `TIMEOUT=270`

**Hierarchy:** `150s ≤ 150s < 210s < 270s` ✅

### Scenario 2: Need faster timeout for testing

**Goal:** Reduce to 60s for quick failure detection

**Changes:**
1. **Page Default + Navigation:** 120s → 60s
   - `src/config.py`: `default=60000`
   - `scripts/deploy-to-cloud-run.sh`: `FEDERALRUNNER_NAVIGATION_TIMEOUT=60000`

2. **Execution:** 180s → 90s (60s + 30s buffer)
   - `src/config.py`: `default=90`
   - `scripts/deploy-to-cloud-run.sh`: `FEDERALRUNNER_EXECUTION_TIMEOUT=90`

3. **Cloud Run:** 240s → 150s (90s + 60s buffer)
   - `.env.deployment`: `TIMEOUT=150`
   - `.env.deployment.example`: `TIMEOUT=150`

**Hierarchy:** `60s ≤ 60s < 90s < 150s` ✅

**Warning:** 60s may be too aggressive for FSA in production. Use for testing only.

---

## Verification Checklist

After changing timeout values:

### Local Testing
```bash
cd mcp-servers/federalrunner-mcp

# Test headless execution
pytest tests/test_execution_local.py::test_federalrunner_execute_wizard_headless -v

# Monitor for timeout values in logs
grep -i "timeout" tests/test_output/*.log
```

### Deployment
```bash
# Deploy with new values
./scripts/deploy-to-cloud-run.sh

# Verify Cloud Run timeout
gcloud run services describe federalrunner-mcp \
    --region us-central1 \
    --format='value(spec.template.spec.timeoutSeconds)'

# Check environment variables
gcloud run services describe federalrunner-mcp \
    --region us-central1 \
    --format='value(spec.template.spec.containers[0].env)'
```

### Production Testing
```bash
# Test from Claude.ai
# Monitor execution times
gcloud run services logs tail federalrunner-mcp \
    --region us-central1 | grep -E "timeout|Execution time|EXECUTION"

# Expected output:
# - "Set page default timeout to Xms"
# - "Execution time: Xms"
# - "[OK] EXECUTION SUCCESSFUL"

# Should NOT see:
# - "Timeout 30000ms exceeded" (old Playwright default)
# - "Timeout Xms exceeded" where X < your config value
```

---

## Troubleshooting

### Issue: Still getting 30-second timeouts

**Cause:** Page default timeout not set

**Fix:** Verify `src/playwright_client.py` has:
```python
self.page.set_default_timeout(self.config.navigation_timeout)
```

**Location:** Immediately after `self.page = await self.context.new_page()`

### Issue: Navigation succeeds but start button times out

**Cause:** Page default timeout too low

**Fix:** Increase Layer 1 (Page Default) to match Layer 2 (Navigation)

### Issue: Cloud Run returns 504 Gateway Timeout

**Cause:** Cloud Run timeout < Execution timeout

**Fix:** Ensure hierarchy is correct:
```
execution_timeout < Cloud Run timeout
```

Increase Cloud Run timeout in `.env.deployment`.

### Issue: Execution times out but pages loaded successfully

**Cause:** Execution timeout too close to navigation timeout

**Fix:** Add 60s+ buffer between layers:
```
navigation_timeout (120s) + 60s buffer = execution_timeout (180s)
```

### Issue: Timeouts work locally but fail in production

**Possibilities:**
1. **Deployment env vars not set** - Check Cloud Run env vars
2. **Cloud Run timeout not updated** - Verify with `gcloud run services describe`
3. **Config changes not deployed** - Redeploy to bake new config into image

---

## Historical Context

### Why 4 Timeout Layers?

1. **Layer 1 (Page Default)** - Playwright default was 30s, too low for FSA
2. **Layer 2 (Navigation)** - FSA page loads take 60-120s
3. **Layer 3 (Execution)** - Need time for full 7-page wizard execution
4. **Layer 4 (Cloud Run)** - HTTP request timeout was killing successful executions

Each layer was discovered through production failures with actual FSA load times.

### Evolution of Values

| Layer | Initial | Current | Reason for Increase |
|-------|---------|---------|---------------------|
| Page Default | 30s (Playwright) | 120s | FSA button clicks slow |
| Navigation | 30s | 120s | FSA pages load in 60-90s |
| Execution | 60s | 180s | Need buffer for retries |
| Cloud Run | 60s | 240s | Was killing 180s executions |

---

## Files Summary

### Configuration Files
1. **`src/config.py`** - Page default, navigation, execution timeouts
2. **`.env.deployment`** - Cloud Run timeout
3. **`.env.deployment.example`** - Cloud Run timeout template

### Implementation Files
1. **`src/playwright_client.py`** - Applies page default and navigation timeouts
2. **`scripts/deploy-to-cloud-run.sh`** - Sets deployment env vars

### Test Files
1. **`tests/test_execution_local.py`** - Local timeout verification

---

## Related Documentation

- **Deployment Guide:** `docs/deployment/DEPLOYMENT_GUIDE.md`
- **Configuration Reference:** `src/config.py` (inline comments)
- **Cloud Run Docs:** https://cloud.google.com/run/docs/configuring/request-timeout
- **Playwright Timeouts:** https://playwright.dev/docs/api/class-page#page-set-default-timeout

---

## Maintenance Notes

**When to Review Timeouts:**
- Monthly based on production logs
- After FSA website changes
- If success rate drops below 95%
- If execution times increase

**Monitoring Metrics:**
- Average execution time
- P95 execution time (95th percentile)
- Timeout error rate
- Success rate on first attempt

**Target Metrics:**
- P95 execution time < 150s
- Timeout error rate < 5%
- Success rate > 95%

If metrics degrade, increase timeouts using scenarios above.
