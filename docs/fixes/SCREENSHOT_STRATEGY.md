# Screenshot Strategy for Production

**Last Updated:** 2025-10-21
**Status:** Production Reference

## Overview

FederalRunner captures screenshots during wizard execution for:
1. **Visual audit trail** - Proof of official government results
2. **Error debugging** - Visual validation loop for runtime errors
3. **Demo purposes** - Show what happens behind the scenes

## Production vs Development

### Development Mode (`headless=False`)
- **Returns:** ALL screenshots captured during execution
- **Purpose:** Complete debugging and testing
- **Location:** Saved to `tests/test_output/screenshots/`
- **Typical count:** 10-20 screenshots (depends on wizard complexity)

### Production Mode (`headless=True`)
- **Returns:** Last 2 screenshots only
- **Purpose:** Balance between context and response size
- **Location:** Not saved to disk, only returned in API response
- **Why 2:** Shows both context and final results

## What the Last 2 Screenshots Show

### For FSA Student Aid Estimator
**Screenshot 1 (second-to-last):**
- Page 7 after clicking continue
- May show partial results or navigation

**Screenshot 2 (final):**
- Official FSA results page
- Shows Student Aid Index (SAI)
- Shows eligibility results

**Demo value:** Shows final official results

---

### For Loan Simulator - Borrow More
**Screenshot 1 (second-to-last):**
- **Page 6: Confirm Current Loan Situation**
- **Shows the 3 loans that were added:**
  - Direct Subsidized Loan: $3,500 @ 5.50%
  - Direct Unsubsidized Loan: $2,000 @ 6.53%
  - Direct PLUS Loan for Parents: $34,500 @ 9.08%
- This is the constructed strategy (Construction Mode evidence)

**Screenshot 2 (final):**
- **Official repayment results page**
- Shows monthly payment estimates
- Shows total repayment amounts
- Shows different repayment plan options

**Demo value:** Shows BOTH the strategy constructed AND the official results

This is **perfect for demos** - you can say:
> "Behind the scenes, Claude read the schema, constructed this optimal 3-loan strategy (screenshot 1), executed the federal simulator, and here are the official results (screenshot 2)."

---

### For Other Wizards
**Last 2 screenshots:**
- Second-to-last: Usually the final data entry page or confirmation
- Final: Official results page

## Screenshot Capture Points

Screenshots are captured at these points during execution:

1. **Initial page** - After navigation and page load
2. **After start action** - After clicking start button
3. **For each page:**
   - After filling all fields
   - After clicking continue button
4. **Final screenshot** - Results page after all pages complete

### Example: Loan Simulator (6 pages)
```
1. Initial page (landing page)
2. After start action (wizard begins)
3. Page 1: Program timing (after fill + after continue)
4. Page 2: Program info (after fill + after continue)
5. Page 3: Family income (after fill + after continue)
6. Page 4: Borrow amount (after fill + after continue)
7. Page 5: Income info (after fill + after continue)
8. Page 6: Current loans (after adding 3 loans + after continue) ← Screenshot 1 returned
9. Final results page ← Screenshot 2 returned

Total: ~18 screenshots captured
Returned in production: Last 2 (screenshots 8 and 9)
```

## Configuration

### Where It's Configured
**File:** `src/playwright_client.py`

**Success case (line 197-205):**
```python
if self.config.headless:
    # Return last 2 screenshots (or all if less than 2)
    response_screenshots = screenshots[-2:] if len(screenshots) >= 2 else screenshots
else:
    # Local dev: include all screenshots for debugging
    response_screenshots = screenshots
```

**Error case (line 231-239):**
```python
if self.config.headless and len(screenshots) > 0:
    # Return last 2 screenshots (or all if less than 2)
    response_screenshots = screenshots[-2:] if len(screenshots) >= 2 else screenshots
else:
    # Local dev: include all screenshots for complete debugging
    response_screenshots = screenshots
```

### How to Change

#### Option 1: Return Only Final Screenshot (Previous Behavior)
```python
response_screenshots = screenshots[-1:] if len(screenshots) >= 1 else screenshots
```

#### Option 2: Return Last 2 Screenshots (Current)
```python
response_screenshots = screenshots[-2:] if len(screenshots) >= 2 else screenshots
```

#### Option 3: Return Last 3 Screenshots
```python
response_screenshots = screenshots[-3:] if len(screenshots) >= 3 else screenshots
```

#### Option 4: Return All Screenshots (Development Mode)
```python
response_screenshots = screenshots
```

## Response Size Impact

### Single Screenshot
- Quality: 60 (JPEG compression)
- Viewport: 1280x1024
- Typical size: 42-52 KB per screenshot
- Response overhead: ~56-70 KB (base64 encoded)

### Two Screenshots (Current)
- Total size: 84-104 KB (2 × 42-52 KB)
- Response overhead: ~112-140 KB (base64 encoded)
- **Still well under MCP protocol limits**

### Why 2 Is Safe
- MCP protocol handles images efficiently
- Modern networks handle 140 KB easily
- Previous timeout issues were due to timeout configs, not response size
- Cloud Run timeout: 240s (plenty of buffer)

## Demo Script Integration

When showing the loan simulator demo, you can say:

**After execution completes:**

> "Let me show you what happened behind the scenes..."
>
> **[Show Screenshot 1 - Page 6 with 3 loans]**
>
> "Claude read the loan schema, which contains federal loan limits, current interest rates, and the optimal strategy. Based on your $40,000 need and freshman status, it automatically constructed this 3-loan mix:
> - Direct Subsidized: $3,500 at 5.50% (cheapest, government pays interest in school)
> - Direct Unsubsidized: $2,000 at 6.53% (your max additional student loan)
> - Parent PLUS: $34,500 at 9.08% (unlimited, fills the gap)
>
> It then submitted this to the official federal loan simulator..."
>
> **[Show Screenshot 2 - Results page]**
>
> "And here are the official results: $557/month for 15 years, totaling about $98,645 in repayment."

This demonstrates **Contract-First Form Automation** - the schema taught the agent the strategy, no hardcoded logic needed.

## Troubleshooting

### Issue: Screenshots show wrong pages

**Cause:** Timing issues or navigation failures

**Debug:** Run in development mode to see all screenshots:
```bash
pytest tests/test_execution_local.py -v
# Check tests/test_output/screenshots/ for all captures
```

### Issue: Response size too large

**Symptoms:** Timeouts, slow responses, MCP errors

**Fix:** Reduce screenshot count:
```python
# Return only final screenshot
response_screenshots = screenshots[-1:]
```

### Issue: Missing context in screenshots

**Symptoms:** Demo doesn't show construction step

**Fix:** Increase screenshot count:
```python
# Return last 3 screenshots
response_screenshots = screenshots[-3:]
```

## Related Documentation

- **Timeout Configuration:** `docs/deployment/TIMEOUT_CONFIGURATION.md`
- **Screenshot Optimization:** `docs/fixes/screenshot-optimization-fix.md` (historical)
- **Playwright Client:** `src/playwright_client.py` (implementation)

## Maintenance Notes

**When to Review:**
- If adding complex multi-step wizards
- If response sizes become problematic
- If demos need different view points

**Current Status:** 2 screenshots is optimal for:
- ✅ Demo value (shows strategy + results)
- ✅ Response size (140 KB, well within limits)
- ✅ Debugging (enough context for errors)
