# Wizard Structure Schema Requirements

## Purpose

Define the canonical JSON structure for representing discovered government form wizards. This schema serves as the contract between the FederalScout Discovery Agent and FederalRunner Execution Agent.

---

## Core Requirements

### REQ-WS-001: JSON File-Based Storage
- **Requirement**: Each discovered wizard MUST be saved as a separate JSON file
- **Location**: `wizards/` directory in workspace root
- **Naming Convention**: `{wizard-name-slug}.json` (lowercase, hyphen-separated)
- **Example**: `fsa-estimator.json`, `ssa-calculator.json`
- **Rationale**: 
  - No database dependency
  - Version controllable via Git
  - Human readable and editable
  - Portable and shareable

### REQ-WS-002: Complete Wizard Metadata
Each wizard structure file MUST contain:
- Unique identifier
- Display name
- Official URL
- Discovery timestamp
- Total number of pages
- Array of page structures
- Discovery agent version

### REQ-WS-003: Page Structure Definition
Each page in the wizard MUST define:
- Page number (sequential)
- Page title/heading
- URL pattern (if different per page)
- Array of input fields
- Continue button selector
- Validation patterns (if any)
- Conditional field rules

### REQ-WS-004: Field Structure Definition
Each field MUST specify:
- Human-readable label (as shown to user)
- Unique field identifier
- HTML selector (CSS selector or ID)
- Field type (text, number, radio, select, typeahead, etc.)
- Interaction method (fill, click, javascript_click, fill_enter)
- Whether field is required
- Default/example value for testing
- Notes about special handling

### REQ-WS-005: Selector Reliability
- Selectors MUST be as specific as possible (prefer IDs over classes)
- If multiple selectors work, document alternative selectors
- Hidden elements MUST note the required interaction method
- Dynamic elements MUST note loading/visibility requirements

---

## Schema Structure

```json
{
  "wizard_id": "string (unique identifier)",
  "name": "string (display name)",
  "url": "string (starting URL)",
  "discovered_at": "ISO 8601 timestamp",
  "discovery_version": "string (FederalScout version)",
  "total_pages": "integer",
  "start_action": {
    "description": "string (what to click to start)",
    "selector": "string (CSS selector)",
    "selector_type": "string (text|id|css)"
  },
  "pages": [
    {
      "page_number": "integer (1-indexed)",
      "page_title": "string",
      "url_pattern": "string (URL after navigation)",
      "fields": [
        {
          "label": "string (user-visible label)",
          "field_id": "string (unique within wizard)",
          "selector": "string (CSS selector)",
          "selector_alternatives": ["string (backup selectors)"],
          "field_type": "string (text|number|radio|select|typeahead|checkbox|group)",
          "interaction": "string (fill|click|select|javascript_click|fill_enter)",
          "required": "boolean",
          "example_value": "string|object",
          "notes": "string (special handling instructions)",
          "sub_fields": [
            "object (for grouped fields like birthdate)"
          ]
        }
      ],
      "continue_button": {
        "text": "string (button text)",
        "selector": "string (CSS selector)"
      },
      "validation": {
        "error_selector": "string (CSS selector for error messages)",
        "required_fields": ["array of field_ids"]
      }
    }
  ]
}
```

---

## Field Type Specifications

### REQ-WS-006: Standard Field Types

**text**: Single-line text input
```json
{
  "field_type": "text",
  "interaction": "fill",
  "example_value": "John Doe"
}
```

**number**: Numeric input field
```json
{
  "field_type": "number",
  "interaction": "fill",
  "example_value": "85000"
}
```

**radio**: Radio button (often hidden)
```json
{
  "field_type": "radio",
  "interaction": "javascript_click",
  "selector": "#fsa_Radio_MaritalStatusUnmarried",
  "notes": "Radio input is hidden, must use JavaScript click"
}
```

**select**: Standard dropdown
```json
{
  "field_type": "select",
  "interaction": "select",
  "example_value": "option_value"
}
```

**typeahead**: Autocomplete search field
```json
{
  "field_type": "typeahead",
  "interaction": "fill_enter",
  "example_value": "Illinois",
  "notes": "Type value and press Enter to select"
}
```

**group**: Multi-field input (e.g., birthdate)
```json
{
  "field_type": "group",
  "label": "Date of birth",
  "sub_fields": [
    {
      "field_id": "month",
      "selector": "#fsa_Input_DateOfBirthMonth",
      "interaction": "fill",
      "example_value": "05"
    },
    {
      "field_id": "day",
      "selector": "#fsa_Input_DateOfBirthDay",
      "interaction": "fill",
      "example_value": "15"
    },
    {
      "field_id": "year",
      "selector": "#fsa_Input_DateOfBirthYear",
      "interaction": "fill",
      "example_value": "2007"
    }
  ]
}
```

---

## Validation Requirements

### REQ-WS-007: Selector Validation
- Discovery MUST test each selector before saving
- If selector fails, alternative selectors MUST be tried
- Final selector MUST be verified to work at discovery time

### REQ-WS-008: Completeness Validation
- All required fields on each page MUST be documented
- Continue button on each page MUST be found and documented
- Final results page MUST be reachable with test data

### REQ-WS-009: Version Control
- Each wizard file MUST include discovery timestamp
- Discovery agent version MUST be recorded
- If wizard changes, new version MUST be created with timestamp

---

## Example: Complete Wizard Structure

See `wizards/fsa-estimator.json` for reference implementation based on FSA Student Aid Estimator testing results.

---

## Non-Requirements

### What NOT to Include:
- ❌ Execution logic (belongs in execution agent)
- ❌ User data mapping rules (belongs in field_mapper.py)
- ❌ Error handling strategies (belongs in execution tools)
- ❌ Authentication details (belongs in auth.py)

### What IS Included:
- ✅ Pure structural information
- ✅ Selector specifications
- ✅ Interaction patterns
- ✅ Field relationships
- ✅ Navigation flow

---

## Success Criteria

A valid wizard structure file MUST:
1. ✅ Load as valid JSON
2. ✅ Contain all required top-level fields
3. ✅ Have at least one page defined
4. ✅ Have all selectors as strings
5. ✅ Have tested and verified selectors
6. ✅ Enable successful execution with test data
7. ✅ Be human-readable and understandable

---

## References

- FSA Test Results: `requirements/reference/fsa-test-results/test_basic_navigation.py`
- Example Structure: `wizards/fsa-estimator.json` (to be created)