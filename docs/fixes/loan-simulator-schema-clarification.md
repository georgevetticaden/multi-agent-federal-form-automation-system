# Loan Simulator Schema Clarification Fix

**Date:** 2025-10-20
**Type:** Schema Description Fix
**Priority:** MEDIUM
**Status:** ✅ Fixed

## Problem

Claude was misinterpreting the `current_loans` field in the loan simulator schema, thinking it asked for **existing loans the user already has**, when it actually asks for **NEW loans to simulate borrowing**.

**Evidence from Production:**

User asked: "Can you use the loan simulator to come up with the ideal set of loans that covers the $77,519 gap?"

Agent responded with:
```json
{
  "current_loans": []  // Empty array!
}
```

Result: Wizard stuck on page 6 with error "Missing Loan Information - You need to add a loan to continue."

Agent's interpretation: "You don't have any existing loans, so I'll pass an empty array."

**Actual requirement:** "Provide the NEW loans you want to borrow to cover the $77,519 gap."

## Root Cause

**Original schema description (line 98):**
```json
"current_loans": {
  "type": "array",
  "description": "List of current student loans (optional, can be empty array)",
  "minItems": 0
}
```

**Problems:**
1. ❌ "current student loans" sounds like existing loans
2. ❌ "optional, can be empty" suggests it's okay to skip
3. ❌ `minItems: 0` allows empty array
4. ❌ Not in `required` array
5. ❌ No guidance on what a typical loan mix looks like

## Solution

### 1. Updated Schema Description

**File:** `wizards/data-schemas/loan-simulator-borrow-more-schema.json`

**Top-level description (line 4):**
```json
"description": "User data required to execute the Federal Student Aid Loan Simulator for borrowing more money for college. IMPORTANT: current_loans are the NEW loans you want to simulate borrowing, not existing loans. For dependent undergrads borrowing $77,519, typical mix: Direct Subsidized $3,500 + Direct Unsubsidized $2,000 + Parent PLUS $72,019. Use current federal interest rates (2024-25: Subsidized/Unsubsidized ~5.5%, PLUS ~8.05%)."
```

**Field description (line 98):**
```json
"current_loans": {
  "type": "array",
  "description": "NEW loans to simulate borrowing (required: at least 1 loan). NOT existing loans - this is the loan mix you want to borrow to cover the borrow_amount. Typically includes Direct Subsidized + Unsubsidized loans for undergrads, or PLUS loans. Must add up to approximately the borrow_amount.",
  "minItems": 1  // Changed from 0
}
```

### 2. Made Field Required

**Before:**
```json
"required": [
  "program_timing",
  "program_type",
  "program_length",
  "dependency_status",
  "family_income",
  "borrow_amount",
  "expected_salary"
]
```

**After:**
```json
"required": [
  "program_timing",
  "program_type",
  "program_length",
  "dependency_status",
  "family_income",
  "borrow_amount",
  "expected_salary",
  "current_loans"  // Added!
]
```

## Expected Behavior After Fix

### User Query
"Can you use the loan simulator to simulate borrowing $77,519 for Northwestern?"

### Agent's Interpretation (Before Fix - Wrong)
"The user has no existing loans, so I'll pass an empty array."
```json
{
  "current_loans": []
}
```

### Agent's Interpretation (After Fix - Correct)
"The user wants to borrow $77,519. For a dependent freshman, typical federal loan mix is:
- Direct Subsidized Loan: $3,500 (max for freshman)
- Direct Unsubsidized Loan: $2,000 (max for dependent freshman)
- Parent PLUS Loan: $72,019 (covers remaining gap)"

```json
{
  "current_loans": [
    {
      "loan_type": "Direct Subsidized Loan",
      "loan_interest_rate": 5.5,
      "loan_balance": 3500
    },
    {
      "loan_type": "Direct Unsubsidized Loan",
      "loan_interest_rate": 5.5,
      "loan_balance": 2000
    },
    {
      "loan_type": "Direct PLUS Loan for Parents",
      "loan_interest_rate": 8.05,
      "loan_balance": 72019
    }
  ]
}
```

## Typical Loan Scenarios

### Dependent Undergraduate (Freshman) - Borrowing $77,519

**Max federal loans for freshman:**
- Direct Subsidized: $3,500
- Direct Unsubsidized: $2,000
- **Total student loans:** $5,500

**Gap:** $77,519 - $5,500 = $72,019
**Solution:** Parent PLUS loan for $72,019

**Array:**
```json
[
  {"loan_type": "Direct Subsidized Loan", "loan_interest_rate": 5.5, "loan_balance": 3500},
  {"loan_type": "Direct Unsubsidized Loan", "loan_interest_rate": 5.5, "loan_balance": 2000},
  {"loan_type": "Direct PLUS Loan for Parents", "loan_interest_rate": 8.05, "loan_balance": 72019}
]
```

### Dependent Undergraduate (Sophomore) - Borrowing $30,000

**Max federal loans for sophomore:**
- Direct Subsidized: $4,500
- Direct Unsubsidized: $2,000
- **Total student loans:** $6,500

**Gap:** $30,000 - $6,500 = $23,500
**Solution:** Parent PLUS loan for $23,500

### Independent Graduate Student - Borrowing $50,000

**Max federal loans for graduate:**
- Direct Graduate Unsubsidized: $20,500 (annual max)
- **Gap:** $50,000 - $20,500 = $29,500
- **Solution:** Grad PLUS loan for $29,500

**Array:**
```json
[
  {"loan_type": "Direct Graduate Unsubsidized Loan", "loan_interest_rate": 7.05, "loan_balance": 20500},
  {"loan_type": "Direct PLUS Loan for Graduate/Professionals", "loan_interest_rate": 8.05, "loan_balance": 29500}
]
```

## Federal Loan Limits Reference

### Dependent Undergraduates (2024-25)
| Year | Subsidized Max | Unsubsidized Max | Total Max |
|------|----------------|------------------|-----------|
| Freshman | $3,500 | $2,000 | $5,500 |
| Sophomore | $4,500 | $2,000 | $6,500 |
| Junior/Senior | $5,500 | $2,000 | $7,500 |

### Independent Undergraduates (2024-25)
| Year | Subsidized Max | Unsubsidized Max | Total Max |
|------|----------------|------------------|-----------|
| Freshman | $3,500 | $6,000 | $9,500 |
| Sophomore | $4,500 | $6,000 | $10,500 |
| Junior/Senior | $5,500 | $7,000 | $12,500 |

### Graduate Students (2024-25)
- **Unsubsidized:** $20,500/year (no subsidized loans for grad students)
- **Grad PLUS:** Unlimited (up to cost of attendance minus other aid)

### Interest Rates (2024-25)
- **Undergraduate Direct Loans:** 5.50%
- **Graduate Direct Unsubsidized:** 7.05%
- **PLUS Loans (Parent or Grad):** 8.05%

## Testing

### Test Scenario 1: Northwestern Freshman ($77,519)

**Input:**
```json
{
  "wizard_id": "loan-simulator-borrow-more",
  "user_data": {
    "program_timing": "future",
    "program_type": "Bachelor's degree",
    "program_length": "4 years",
    "dependency_status": "dependent",
    "school_location": "Illinois",
    "school_name": "Northwestern University",
    "family_income": "$110,001+",
    "borrow_amount": 77519,
    "expected_salary": 60000,
    "income_growth_rate": 3,
    "current_loans": [
      {"loan_type": "Direct Subsidized Loan", "loan_interest_rate": 5.5, "loan_balance": 3500},
      {"loan_type": "Direct Unsubsidized Loan", "loan_interest_rate": 5.5, "loan_balance": 2000},
      {"loan_type": "Direct PLUS Loan for Parents", "loan_interest_rate": 8.05, "loan_balance": 72019}
    ]
  }
}
```

**Expected:** Wizard completes successfully, shows repayment simulations for $77,519 total debt.

### Test Scenario 2: Moderate Borrowing ($20,000)

**Input:**
```json
{
  "wizard_id": "loan-simulator-borrow-more",
  "user_data": {
    "program_timing": "current",
    "program_type": "Bachelor's degree",
    "program_length": "4 years",
    "dependency_status": "dependent",
    "family_income": "$75,000 - $110,000",
    "borrow_amount": 20000,
    "expected_salary": 50000,
    "current_loans": [
      {"loan_type": "Direct Subsidized Loan", "loan_interest_rate": 5.5, "loan_balance": 10000},
      {"loan_type": "Direct Unsubsidized Loan", "loan_interest_rate": 5.5, "loan_balance": 5000},
      {"loan_type": "Direct PLUS Loan for Parents", "loan_interest_rate": 8.05, "loan_balance": 5000}
    ]
  }
}
```

**Expected:** Wizard completes, shows manageable repayment options.

## Files Changed

1. ✅ `/wizards/data-schemas/loan-simulator-borrow-more-schema.json`
   - Line 4: Updated main description with examples
   - Line 14: Added `current_loans` to required array
   - Line 98: Updated field description to clarify NEW loans
   - Line 99: Changed `minItems: 0` → `minItems: 1`

## Lessons Learned

### Lesson 1: Schema Descriptions Are Critical
- Field names can be misleading (`current_loans` sounds like existing loans)
- Descriptions must be **crystal clear** about intent
- Examples in descriptions help Claude understand context

### Lesson 2: Required vs Optional Fields
- If a field is **necessary for workflow**, mark it `required`
- Use `minItems` to enforce minimum array length
- Don't rely on optional fields with default values

### Lesson 3: Domain Knowledge in Schemas
- Include realistic examples in descriptions
- Provide typical values/ranges (interest rates, loan amounts)
- Reference limits/constraints (federal loan max amounts)

### Lesson 4: Test with Real User Queries
- "Cover the $77,519 gap" is how real users talk
- Claude needs to map natural language → loan structure
- Examples in schema help bridge this gap

## Related Documentation

- **Repeatable Field Fix:** `docs/fixes/repeatable-field-fix.md`
- **Loan Simulator Wizard Data:** `wizards/wizard-data/loan-simulator-borrow-more.json`
- **Loan Simulator Schema:** `wizards/data-schemas/loan-simulator-borrow-more-schema.json`

## References

- Federal Student Aid Loan Limits: https://studentaid.gov/understand-aid/types/loans/subsidized-unsubsidized
- Federal Loan Interest Rates: https://studentaid.gov/understand-aid/types/loans/interest-rates
- Loan Simulator: https://studentaid.gov/loan-simulator/
