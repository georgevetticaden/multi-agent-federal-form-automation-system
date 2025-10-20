# Fix: ID Selector Handling in Start Action and Continue Button

**Date:** 2025-10-20
**Affected Component:** FederalRunner Playwright Client
**Severity:** High (blocking Loan Simulator start)
**Status:** ✅ Fixed

## Problem

The Loan Simulator wizard's `start_action` had `selector_type: "id"` but the selector was missing the `#` prefix required by CSS selectors.

**Wizard Structure:**
```json
"start_action": {
  "description": "Click to start the Borrow More simulator without logging in",
  "selector": "fsa_LinkButton_LoanSimulatorLandingRepayStrategyStartUnauth3",
  "selector_type": "id"
}
```

**Error:**
```
Failed to execute start action (selector: fsa_LinkButton_LoanSimulatorLandingRepayStrategyStartUnauth3).
Start button may not be visible or selector may be incorrect.
Page.click: Timeout 30000ms exceeded.
```

**Actual HTML:**
```html
<button id="fsa_LinkButton_LoanSimulatorLandingRepayStrategyStartUnauth3">
  Or Start From Scratch
</button>
```

## Root Cause

The `_execute_start_action()` and `_click_continue()` methods only handled `SelectorType.TEXT`, treating everything else as CSS selectors. When `selector_type: "id"` was used without the `#` prefix, Playwright couldn't find the element.

**Before:**
```python
async def _execute_start_action(self, start_action: StartAction):
    try:
        if start_action.selector_type == SelectorType.TEXT:
            await self.page.get_by_text(start_action.selector, exact=True).click()
        else:
            # Default: treat as CSS selector (requires # for IDs!)
            await self.page.click(start_action.selector)
```

This failed because `click("fsa_LinkButton...")` is invalid CSS (needs `#fsa_LinkButton...`).

## Solution

Added explicit handling for `SelectorType.ID` with automatic `#` prefix injection:

```python
async def _execute_start_action(self, start_action: StartAction):
    try:
        if start_action.selector_type == SelectorType.TEXT:
            await self.page.get_by_text(start_action.selector, exact=True).click()
        elif start_action.selector_type == SelectorType.ID:
            # ID selector - ensure it has # prefix
            selector = start_action.selector
            if not selector.startswith('#'):
                selector = f'#{selector}'
            await self.page.click(selector)
        else:
            # Default: CSS selector
            await self.page.click(start_action.selector)
```

**Benefits:**
- Works with or without `#` prefix (backward compatible)
- Explicit handling of ID vs CSS vs TEXT selector types
- Same logic applied to both `_execute_start_action()` and `_click_continue()`

## Files Changed

### `src/playwright_client.py`

**1. `_execute_start_action()` (lines 463-475)**
```python
if start_action.selector_type == SelectorType.TEXT:
    await self.page.get_by_text(start_action.selector, exact=True).click()
elif start_action.selector_type == SelectorType.ID:
    selector = start_action.selector
    if not selector.startswith('#'):
        selector = f'#{selector}'
    await self.page.click(selector)
else:
    await self.page.click(start_action.selector)
```

**2. `_click_continue()` (lines 358-370)**
```python
if continue_button.selector_type == SelectorType.TEXT:
    await self.page.get_by_text(continue_button.selector, exact=True).click()
elif continue_button.selector_type == SelectorType.ID:
    selector = continue_button.selector
    if not selector.startswith('#'):
        selector = f'#{selector}'
    await self.page.click(selector)
else:
    await self.page.click(continue_button.selector)
```

## Selector Type Handling

### SelectorType.TEXT
Uses Playwright's `get_by_text()` for text-based selection:
```python
await self.page.get_by_text("Continue", exact=True).click()
```

### SelectorType.ID
Converts to CSS ID selector:
```python
# Input: "fsa_Button_WizardContinue" or "#fsa_Button_WizardContinue"
# Output: "#fsa_Button_WizardContinue"
await self.page.click("#fsa_Button_WizardContinue")
```

### SelectorType.CSS (default)
Uses selector as-is:
```python
await self.page.click("#fsa_Button_WizardContinue")  # Already has #
await self.page.click(".submit-button")              # Class selector
await self.page.click("button[type='submit']")       # Attribute selector
```

## Why This Happened

The FederalScout discovery agent saves selectors in different formats:
- IDs without `#`: `"fsa_Button_WizardContinue"`
- IDs with `#`: `"#fsa_Button_WizardContinue"`

Both are valid in the wizard structure, but execution needs to handle both cases.

## Design Decision: Auto-Prefix vs Strict Validation

**Option 1: Auto-prefix (CHOSEN)**
```python
if not selector.startswith('#'):
    selector = f'#{selector}'
```
✅ Backward compatible
✅ Forgiving (works with both formats)
✅ Less brittle for future wizard discoveries

**Option 2: Strict validation (NOT CHOSEN)**
```python
if not selector.startswith('#'):
    raise ValueError(f"ID selector must start with #: {selector}")
```
❌ Breaks existing wizard structures
❌ Requires re-discovery of all wizards
❌ More work for FederalScout agent

## Testing

Validated with:
- `tests/test_execution_local.py::test_loan_simulator_execute_wizard_non_headless`
- Start action: `selector_type: "id"`, `selector: "fsa_LinkButton..."`
- Result: ✅ Button clicked successfully

**Log output:**
```
->  Executing start action: fsa_LinkButton_LoanSimulatorLandingRepayStrategyStartUnauth3
  ->  Start action: fsa_LinkButton_LoanSimulatorLandingRepayStrategyStartUnauth3
```

No error → auto-prefix worked!

## Future Improvements

### 1. Update FederalScout Discovery
Could standardize on always including `#` prefix for ID selectors:
```python
if element_id:
    selector = f"#{element_id}"  # Always include #
    selector_type = "id"
```

### 2. Validation in Wizard Structure Schema
Could add validation rule:
```json
{
  "if": {"properties": {"selector_type": {"const": "id"}}},
  "then": {"properties": {"selector": {"pattern": "^#.*"}}}
}
```

But this would break existing wizard structures, so auto-prefix is better.

## Related Issues

- FSA Estimator uses CSS selectors with `#` prefix → Works with default case
- Loan Simulator uses ID selector without `#` → Fixed by auto-prefix

## References

- Playwright Selectors: https://playwright.dev/python/docs/selectors
- CSS ID Selector Syntax: https://developer.mozilla.org/en-US/docs/Web/CSS/ID_selectors
- Wizard Structure: `/wizards/wizard-structures/loan-simulator-borrow-more.json`
