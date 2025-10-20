# Fix: Unicode Apostrophe in Dropdown Selections

**Date:** 2025-10-20
**Affected Component:** FederalRunner Playwright Client
**Severity:** Medium (blocking Loan Simulator execution)
**Status:** ✅ Fixed

## Problem

FSA website dropdowns use Unicode right single quotation mark (`\u2019` aka `'`) instead of ASCII apostrophe (`'`) in option text. This caused dropdown selection failures.

**Example:**
- Schema/User Data: `"Bachelor's degree"` (ASCII apostrophe `'`)
- HTML Dropdown: `"Bachelor's degree"` (Unicode `\u2019`)
- Error: `Page.select_option: Timeout 30000ms exceeded - did not find some options`

## Root Cause

Playwright's `select_option()` matches options by:
1. Value attribute
2. Label (visible text)

When the visible text contains Unicode characters, exact matching fails if we only try ASCII.

## Solution

Implemented **multi-strategy selection** that tries 4 different approaches in order:

```python
strategies = [
    ("original value", lambda: self.page.select_option(field.selector, value_str)),
    ("unicode apostrophe", lambda: self.page.select_option(field.selector, value_str.replace("'", "\u2019"))),
    ("label (original)", lambda: self.page.select_option(field.selector, label=value_str)),
    ("label (unicode)", lambda: self.page.select_option(field.selector, label=value_str.replace("'", "\u2019")))
]
```

**Fallback logic:** If one strategy fails, try the next. Only raise error if all 4 fail.

## Files Changed

### `src/playwright_client.py` (lines 303-338)

**Before:**
```python
elif field.interaction == InteractionType.SELECT:
    # Dropdown select
    await self.page.select_option(field.selector, str(value))
    logger.debug(f"    -> Selected dropdown option")
```

**After:**
```python
elif field.interaction == InteractionType.SELECT:
    # Dropdown select with Unicode apostrophe handling
    value_str = str(value)
    selection_successful = False
    last_error = None

    strategies = [
        ("original value", lambda: self.page.select_option(field.selector, value_str)),
        ("unicode apostrophe", lambda: self.page.select_option(field.selector, value_str.replace("'", "\u2019"))),
        ("label (original)", lambda: self.page.select_option(field.selector, label=value_str)),
        ("label (unicode)", lambda: self.page.select_option(field.selector, label=value_str.replace("'", "\u2019")))
    ]

    for strategy_name, strategy_func in strategies:
        try:
            await strategy_func()
            selection_successful = True
            logger.debug(f"    -> Selected dropdown option using strategy: {strategy_name}")
            break
        except Exception as e:
            last_error = e
            logger.debug(f"    -> Strategy '{strategy_name}' failed: {str(e)[:100]}")
            continue

    if not selection_successful:
        raise last_error
```

## Test Results

**Loan Simulator Test (test_loan_simulator_execute_wizard_non_headless):**

**Before optimization (30-second timeout):**
```
Page 2: Tell us about your future program
  Filling program_type: Bachelor's degree
    -> Strategy 'original value' failed: Timeout 30000ms exceeded (31s total!)
    -> Selected dropdown option using strategy: unicode apostrophe ✅
```

**After optimization (5-second timeout):**
```
Page 2: Tell us about your future program
  Filling program_type: Bachelor's degree
    -> Strategy 'original value' failed: Timeout 5000ms exceeded (5s)
    -> Selected dropdown option using strategy: unicode apostrophe ✅ (6s total)
```

**Performance improvement:** 31s → 6s (5× faster!)

## Benefits

1. **Backward Compatible:** Still works with ASCII apostrophes
2. **Unicode Support:** Handles Unicode right single quotation marks (`\u2019`)
3. **Robust:** Tries both value and label matching
4. **Debuggable:** Logs which strategy succeeded

## Related Issues

- Also applies to sub-fields in repeatable fields (see `repeatable-field-fix.md`)
- Unicode handling is consistent across main fields and sub-fields

## Performance Optimization (✅ IMPLEMENTED)

**Initial implementation:** 30-second default timeout per strategy → 31s for Unicode dropdowns

**Optimized implementation:** 5-second timeout per strategy → 6s for Unicode dropdowns

This optimization is **critical for production** where Cloud Run may timeout if a single field takes >20 seconds.

**Implementation:** Added `timeout=5000` parameter to all `select_option()` calls (both main fields and sub-fields).

## Future Improvements

Additional optimizations (not critical):
1. Detect if value contains apostrophe → Try Unicode strategy first (would reduce to ~1s)
2. Inspect dropdown options to detect Unicode → Skip ASCII strategy entirely
3. Cache Unicode detection per selector → Avoid retries on subsequent calls

For now, the 5-second optimization is sufficient for production use.

## Testing

Validated with:
- `tests/test_execution_local.py::test_loan_simulator_execute_wizard_non_headless`
- Dropdown: `program_type = "Bachelor's degree"` (Unicode in HTML)
- Result: ✅ Selection successful using "unicode apostrophe" strategy

## References

- Unicode Right Single Quotation Mark: https://www.unicode.org/charts/PDF/U2000.pdf (U+2019)
- Playwright select_option: https://playwright.dev/python/docs/api/class-page#page-select-option
- Related fix: `repeatable-field-fix.md` (uses same Unicode handling for sub-fields)
