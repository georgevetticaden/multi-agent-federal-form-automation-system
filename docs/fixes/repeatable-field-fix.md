# Fix: Repeatable Field Handling (Add Loan Workflow)

**Date:** 2025-10-20
**Affected Component:** FederalRunner Playwright Client
**Severity:** High (critical for Loan Simulator wizard)
**Status:** ✅ Fixed

## Problem

The Loan Simulator wizard has a **repeatable field** on Page 6 where users can add multiple loans by:
1. Clicking "Add a Loan" button
2. Filling in: Loan Type (dropdown), Interest Rate (%), Balance ($)
3. Clicking "Save" button
4. Repeating for each additional loan

This pattern wasn't implemented in FederalRunner, causing execution to fail when trying to fill the `current_loans` field.

**Error:**
```
Failed to fill field 'current_loans' (selector: #loan_table).
Error: Page.click: Timeout 30000ms exceeded.
  - waiting for locator("#loan_table")
```

## Root Cause

The wizard structure defines this field as:
```json
{
  "field_id": "current_loans",
  "field_type": "group",
  "selector": "#loan_table",
  "interaction": "click",
  "repeatable": true,
  "add_button_selector": "#fsa_IconLinkButton_LoanSimulatorWizardLoansAddNewLoan",
  "sub_fields": [
    {"field_id": "loan_type", "selector": "#fsa_Select_...", "interaction": "select"},
    {"field_id": "loan_interest_rate", "selector": "#fsa_Input_...", "interaction": "fill"},
    {"field_id": "loan_balance", "selector": "#fsa_Input_...", "interaction": "fill"}
  ]
}
```

The execution code was trying to `click("#loan_table")` (which is a table, not a button), instead of implementing the multi-step workflow.

## Solution

Implemented **repeatable field workflow** in `_fill_field()`:

### 1. Detect Array/Group Fields
```python
if field.field_type == FieldType.GROUP and isinstance(value, list):
    # This is a repeatable field
```

### 2. Handle Empty Arrays
```python
if len(value) == 0:
    # Skip field entirely (don't click anything)
    logger.debug(f"    -> Skipped group field (empty array - no items to add)")
    return
```

### 3. Add Each Item
```python
for index, item_data in enumerate(value):
    # Click "Add" button
    await self.page.click(field.add_button_selector)
    await self.page.wait_for_timeout(500)

    # Fill each sub-field
    for sub_field in field.sub_fields:
        sub_field_value = item_data.get(sub_field.field_id)
        # Fill based on interaction type (fill, select, etc.)

    # Click "Save" button
    await self.page.get_by_text("Save", exact=True).click()
    await self.page.wait_for_timeout(500)
```

## Files Changed

### `src/playwright_client.py` (lines 281-342)

Added special handling before main interaction logic:

```python
# Special handling for array/group fields (repeatable fields)
if field.field_type == FieldType.GROUP and isinstance(value, list):
    if len(value) == 0:
        logger.debug(f"    -> Skipped group field (empty array - no items to add)")
        return
    else:
        logger.debug(f"    -> Repeatable field: adding {len(value)} item(s)")

        for index, item_data in enumerate(value):
            logger.debug(f"       Adding item {index + 1}/{len(value)}")

            # Click Add button
            await self.page.click(field.add_button_selector)
            await self.page.wait_for_timeout(500)

            # Fill sub-fields
            for sub_field in field.sub_fields:
                sub_field_value = item_data.get(sub_field.field_id)

                if sub_field.interaction == InteractionType.FILL:
                    await self.page.fill(sub_field.selector, str(sub_field_value))
                elif sub_field.interaction == InteractionType.SELECT:
                    # Use Unicode handling strategy
                    value_str = str(sub_field_value)
                    try:
                        await self.page.select_option(sub_field.selector, value_str)
                    except Exception:
                        await self.page.select_option(sub_field.selector, value_str.replace("'", "\u2019"))

            # Click Save button
            await self.page.get_by_text("Save", exact=True).click()
            await self.page.wait_for_timeout(500)

        logger.debug(f"    -> Completed adding {len(value)} item(s)")
        return
```

### `tests/test_execution_local.py` (lines 103-114)

Updated test data to actually add loans:

```python
"current_loans": [
    {
        "loan_type": "Direct Subsidized Loan",
        "loan_interest_rate": 6.39,
        "loan_balance": 10000
    },
    {
        "loan_type": "Direct PLUS Loan for Graduate/Professionals",
        "loan_interest_rate": 8.94,
        "loan_balance": 40000
    }
]
```

## Workflow Details

### Visual Flow
```
Page 6: "You have 0 loans"
  ↓
Click "Add a Loan"
  ↓
Form appears:
  - Loan Type: [dropdown]
  - Interest Rate: [input]
  - Total Balance: [input]
  - [Save] [Cancel]
  ↓
Fill fields with item_data[0]
  ↓
Click "Save"
  ↓
Table shows: "You have 1 loans" ($10,000)
  ↓
Click "Add a Loan" again
  ↓
Fill fields with item_data[1]
  ↓
Click "Save"
  ↓
Table shows: "You have 2 loans" ($50,000 total)
  ↓
Click "Continue"
```

## Critical Design Decisions

### 1. Save Button Detection
Using `get_by_text("Save", exact=True)` is reliable because:
- "Save" button appears after clicking "Add a Loan"
- No ID selector in wizard structure
- Text matching is most robust for this pattern

### 2. Unicode Handling in Sub-Fields
Sub-field dropdowns also need Unicode apostrophe handling:
```python
try:
    await self.page.select_option(sub_field.selector, value_str)
except Exception:
    await self.page.select_option(sub_field.selector, value_str.replace("'", "\u2019"))
```

Simplified version (2 strategies instead of 4) since sub-fields are less critical for performance.

### 3. Empty Array Handling
When `current_loans: []`, skip the field entirely:
- Don't click Add button
- Don't try to click the table
- Just proceed to Continue button

This matches the use case: "No existing loans, just calculating new borrowing"

## Use Case: Financial Aid Gap Analysis

This fix enables the **multi-step financial aid workflow**:

1. User runs FSA Estimator → Gets financial aid estimate
2. Agent calculates gap: `school_cost - financial_aid = gap`
3. Agent uses Loan Simulator with optimized loan mix to cover gap
4. User sees realistic loan scenarios to make informed decision

**Example:**
- School cost: $30,000/year
- Financial aid: $15,000/year
- Gap: $15,000/year
- Existing loans: $10,000 subsidized + $40,000 PLUS
- Need to borrow: Additional $15,000/year × 4 years = $60,000

## Testing

Validated with:
- `tests/test_execution_local.py::test_loan_simulator_execute_wizard_non_headless`
- Test adds 2 loans to the table
- Expected result: "You have 2 loans" with total balance $50,000

## Future Improvements

### 1. Support Other Repeatable Patterns
This implementation assumes:
- Single "Add" button
- Single "Save" button (found by text)
- Form appears/disappears on Add/Save

Other patterns might need:
- Index-based selectors for Edit/Remove buttons
- Different save button selectors
- Multi-step forms with validation

### 2. Validation Between Adds
Currently no validation between loan additions. Could add:
- Screenshot after each Save
- Verify table row count increases
- Verify total balance updates

### 3. Error Recovery
If Save fails:
- Currently raises error and stops
- Could add retry logic
- Could click Cancel and skip that item

## References

- Wizard Structure: `/wizards/wizard-structures/loan-simulator-borrow-more.json` (Page 6)
- User Data Schema: `/wizards/data-schemas/loan-simulator-borrow-more-schema.json`
- Related fix: `unicode-dropdown-fix.md` (handles Unicode in sub-field dropdowns)

## Impact

✅ **Unblocks:** Complete Loan Simulator wizard execution
✅ **Enables:** Multi-wizard financial aid workflows
✅ **Pattern:** Reusable for other repeatable fields (expenses, family members, etc.)
