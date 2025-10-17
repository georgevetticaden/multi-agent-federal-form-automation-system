# Contract-First Form Automation Requirements

**Document ID:** REQ-CONTRACT-001
**Status:** Draft
**Last Updated:** 2025-10-16

---

## Overview

**Contract-First Form Automation** is a design pattern where visual form discovery automatically generates type-safe contracts (JSON Schemas) that bridge human interaction and automated execution. This document defines the complete architecture spanning FederalScout (discovery) and FederalRunner (execution).

---

## Pattern Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    CONTRACT-FIRST FORM AUTOMATION                        │
│                                                                          │
│  Vision Discovery → Structure + Contract → Type-Safe Execution          │
└─────────────────────────────────────────────────────────────────────────┘

                       UNIVERSAL SCHEMA (v1)
                ┌──────────────────────────────────┐
                │  Wizard Structure Schema         │
                │  (Playwright Execution Format)   │
                │                                  │
                │  Defines what ALL wizards must   │
                │  look like for execution:        │
                │  • wizard_id, url, pages[]       │
                │  • fields[] with selectors       │
                │  • interaction types             │
                │  • continue_button structure     │
                │                                  │
                │  Location:                       │
                │  schemas/wizard-structure-v1.    │
                │  schema.json                     │
                └──────────────────────────────────┘
                              ↑ conformsTo
                              │
┌─────────────────────────────┼─────────────────────────────────────────┐
│                             │                                         │
│         PHASE 1: DISCOVERY (FederalScout Agent)                          │
│                 Claude Desktop + Playwright                            │
│                                                                        │
│  ┌─────────────┐   Vision      ┌──────────────────────┐             │
│  │   Claude    │───────────────→│  Government Form     │             │
│  │  Desktop +  │   Playwright   │  (FSA Website)       │             │
│  │   Human     │   screenshots  │                      │             │
│  └─────────────┘                └──────────────────────┘             │
│         │                                                              │
│         ↓ discovers page-by-page (federalscout_save_page_metadata)       │
│  ┌────────────────────────────────────────────────────────────┐      │
│  │        ARTIFACT 1: Wizard Data (Instance)                  │      │
│  │  wizards/wizard-data/fsa-student-aid-estimator.json       │      │
│  │                                                             │      │
│  │  {                                                          │      │
│  │    "wizard_id": "fsa-student-aid-estimator",              │      │
│  │    "wizard_name": "FSA Student Aid Estimator",            │      │
│  │    "url": "https://studentaid.gov/aid-estimator/",        │      │
│  │    "start_action": {                                       │      │
│  │      "selector": "#startButton",                           │      │
│  │      "interaction": "click"                                │      │
│  │    },                                                       │      │
│  │    "pages": [                                               │      │
│  │      {                                                      │      │
│  │        "page_number": 1,                                    │      │
│  │        "page_title": "Student Information",                │      │
│  │        "fields": [                                          │      │
│  │          {                                                  │      │
│  │            "field_id": "birth_month",    ← Links to schema │      │
│  │            "label": "Date of birth - Month",               │      │
│  │            "selector": "#fsa_Input_DateOfBirthMonth",     │      │
│  │            "field_type": "number",                         │      │
│  │            "interaction": "fill",                          │      │
│  │            "required": true                                │      │
│  │          },                                                 │      │
│  │          {                                                  │      │
│  │            "field_id": "parent_income",                    │      │
│  │            "label": "Parent Income",                       │      │
│  │            "selector": "#fsa_Input_ParentIncome",         │      │
│  │            "field_type": "number",                         │      │
│  │            "interaction": "fill",                          │      │
│  │            "required": true                                │      │
│  │          }                                                  │      │
│  │        ],                                                   │      │
│  │        "continue_button": {                                │      │
│  │          "selector": "#continueBtn",                       │      │
│  │          "interaction": "click"                            │      │
│  │        }                                                    │      │
│  │      }                                                      │      │
│  │    ],                                                       │      │
│  │    "discovered_at": "2025-10-16T...",                      │      │
│  │    "discovery_version": "1.0"                              │      │
│  │  }                                                          │      │
│  │                                                             │      │
│  │  Purpose: Complete Playwright execution data              │      │
│  │  Used by: FederalRunner (loads this + schema for execution)   │      │
│  │  Conforms to: schemas/wizard-structure-v1.schema.json     │      │
│  └────────────────────────────────────────────────────────────┘      │
│         │                                                              │
│         ↓ Claude generates schema (federalscout_save_schema)             │
│  ┌────────────────────────────────────────────────────────────┐      │
│  │     ARTIFACT 2: User Data Schema (THE CONTRACT)            │      │
│  │  wizards/wizard-schemas/fsa-student-aid-estimator-schema.  │      │
│  │  json                                                       │      │
│  │                                                             │      │
│  │  {                                                          │      │
│  │    "$schema": "http://json-schema.org/draft-07/schema#",  │      │
│  │    "$id": "https://formflow.io/schemas/fsa-estimator.json",│      │
│  │    "title": "FSA Student Aid Estimator Input Schema",     │      │
│  │    "description": "User data required for FSA execution",  │      │
│  │    "version": "1.0.0",                                      │      │
│  │    "discoveredAt": "2025-10-16T...",                       │      │
│  │    "sourceUrl": "https://studentaid.gov/aid-estimator/",  │      │
│  │    "type": "object",                                        │      │
│  │    "required": ["birth_month", "birth_year", "state", ...],│      │
│  │    "properties": {                                          │      │
│  │      "birth_month": {            ← Matches field_id       │      │
│  │        "type": "string",                                    │      │
│  │        "pattern": "^(0[1-9]|1[0-2])$",                     │      │
│  │        "description": "Month (01-12)",                     │      │
│  │        "examples": ["05"]                                   │      │
│  │      },                                                     │      │
│  │      "parent_income": {          ← Matches field_id       │      │
│  │        "type": "integer",                                   │      │
│  │        "minimum": 0,                                        │      │
│  │        "description": "Parent annual income in dollars",   │      │
│  │        "examples": [85000]                                  │      │
│  │      }                                                      │      │
│  │    }                                                        │      │
│  │  }                                                          │      │
│  │                                                             │      │
│  │  Purpose: Defines what data users must provide            │      │
│  │  Used by: Claude (reads to collect data from users)       │      │
│  │           FederalRunner (validates user_data before execution) │      │
│  │  Generated by: Claude analyzing wizard data               │      │
│  └────────────────────────────────────────────────────────────┘      │
│                                                                        │
│  Key Link: field_id connects wizard data ↔ schema                    │
│    wizard field_id="birth_month" → schema property "birth_month"     │
│                                                                        │
└────────────────────────────────────────────────────────────────────────┘
                              │
                              │ THE CONTRACT (User Data Schema)
                              │
                              ↓
┌────────────────────────────────────────────────────────────────────────┐
│                                                                         │
│         PHASE 2: EXECUTION (FederalRunner Agent)                           │
│                 Claude.ai + Cloud Run                                   │
│                                                                         │
│  ┌─────────────┐                                                       │
│  │    User     │  "Hey Claude, I just finished touring Northwestern   │
│  │   (Voice)   │   and need to figure out if we can afford it. Can    │
│  │  Samsung    │   you calculate my federal student aid? I'm 17, born │
│  │  Galaxy     │   in May 2007, single, from Illinois, and I'll be a  │
│  │  Fold 7     │   freshman in fall 2026. My parents are married, also│
│  │             │   in Illinois, family of four. Income $120k, $30k in  │
│  │             │   savings, no child support, and I didn't have any    │
│  │             │   income. Northwestern costs like $85k a year."       │
│  └─────────────┘                                                       │
│         │                                                               │
│         ↓                                                               │
│  ┌─────────────┐                                                       │
│  │  Claude.ai  │  Step 1: federalrunner_list_wizards()                    │
│  │   Mobile    │  → sees "FSA Student Aid Estimator"                  │
│  │             │                                                        │
│  │             │  Step 2: federalrunner_get_wizard_info(                  │
│  │             │            "fsa-student-aid-estimator")               │
│  └─────────────┘                                                       │
│         │                                                               │
│         ↓ receives User Data Schema                                    │
│  ┌──────────────────────────────────────────────────────────┐         │
│  │  User Data Schema (THE CONTRACT)                         │         │
│  │                                                            │         │
│  │  Tells Claude what to extract from user's message:       │         │
│  │  • birth_month: string, pattern "^(0[1-9]|1[0-2])$"     │         │
│  │  • birth_year: string, pattern "^[12][0-9]{3}$"         │         │
│  │  • state: string, enum [all states]                      │         │
│  │  • parent_income: integer, minimum 0                     │         │
│  │  • ... (all required fields)                             │         │
│  └──────────────────────────────────────────────────────────┘         │
│         │                                                               │
│         ↓ Claude transforms natural language → schema fields           │
│  ┌──────────────────────────────────────────────────────────┐         │
│  │        User Data (Claude's Extraction)                   │         │
│  │                                                            │         │
│  │  {                                                         │         │
│  │    "birth_month": "05",        // "May" → "05"           │         │
│  │    "birth_year": "2007",       // "17" → "2007"          │         │
│  │    "state": "Illinois",                                   │         │
│  │    "marital_status": "unmarried",  // "single" → ...     │         │
│  │    "grade_level": "freshman",                             │         │
│  │    "parent_income": 120000,    // "$120k" → 120000       │         │
│  │    "parent_assets": 30000,     // "$30k" → 30000         │         │
│  │    "student_income": 0,        // "didn't have" → 0      │         │
│  │    "family_size": "4",         // "family of four" → 4   │         │
│  │    ...                                                     │         │
│  │  }                                                         │         │
│  └──────────────────────────────────────────────────────────┘         │
│         │                                                               │
│         ↓ Step 3: federalrunner_execute_wizard(wizard_id, user_data)      │
│  ┌────────────────────────────────────────────────────────────┐       │
│  │         FederalRunner Execution Engine (Cloud Run)             │       │
│  │                                                              │       │
│  │  1. Load User Data Schema                                  │       │
│  │     └─→ Validate user_data against schema (jsonschema)     │       │
│  │         ✅ All required fields present                      │       │
│  │         ✅ Types correct (string, integer)                  │       │
│  │         ✅ Patterns match (birth_month matches regex)       │       │
│  │                                                              │       │
│  │  2. Load Wizard Data                                        │       │
│  │     └─→ Get Playwright execution instructions              │       │
│  │                                                              │       │
│  │  3. Map user data to wizard via field_id                   │       │
│  │     user_data["birth_month"] = "05"                        │       │
│  │         ↓ field_id="birth_month"                           │       │
│  │     wizard.fields[0].selector = "#fsa_Input_DateOfBirth..."│       │
│  │         ↓ interaction="fill"                               │       │
│  │     page.fill("#fsa_Input_DateOfBirthMonth", "05")        │       │
│  │                                                              │       │
│  │  4. Execute atomically with Playwright                      │       │
│  │     • Launch headless browser (WebKit)                      │       │
│  │     • Navigate to FSA URL                                   │       │
│  │     • Execute start_action                                  │       │
│  │     • For each page:                                        │       │
│  │       - Fill all fields (mapped via field_id)              │       │
│  │       - Take screenshot                                     │       │
│  │       - Click continue_button                              │       │
│  │     • Extract results from final page                       │       │
│  │     • Close browser                                         │       │
│  │                                                              │       │
│  │  5. Return results                                          │       │
│  └────────────────────────────────────────────────────────────┘       │
│         │                                                               │
│         ↓                                                               │
│  ┌────────────────────────────────────────────────────────────┐       │
│  │            Results + Audit Trail                           │       │
│  │                                                              │       │
│  │  {                                                           │       │
│  │    "success": true,                                          │       │
│  │    "results": {                                              │       │
│  │      "student_aid_index": "19514",                          │       │
│  │      "eligibility": "Eligible for federal aid",            │       │
│  │      "pell_grant_estimate": "$3,500"                        │       │
│  │    },                                                        │       │
│  │    "screenshots": [base64...],  // All 7 pages             │       │
│  │    "execution_time_ms": 8500                                │       │
│  │  }                                                           │       │
│  └────────────────────────────────────────────────────────────┘       │
│         │                                                               │
│         ↓                                                               │
│  ┌─────────────┐                                                       │
│  │  Claude.ai  │  "Your Student Aid Index (SAI) is $19,514. This     │
│  │   Mobile    │   means your family is expected to contribute        │
│  │             │   $19,514 toward college costs. Based on             │
│  │             │   Northwestern's $85,000 annual cost, you would      │
│  │             │   need approximately $65,486 in financial aid..."    │
│  └─────────────┘                                                       │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘

KEY INSIGHT: The User Data Schema is the CONTRACT
- FederalScout generates it (vision → schema)
- Claude reads it (schema → data collection)
- FederalRunner enforces it (validation → execution)
- field_id links schema properties to wizard selectors
```

---

## Core Principles

### 1. Two Artifacts, One Discovery

FederalScout discovers a wizard and generates **two artifacts**:

1. **Wizard Data** - Complete Playwright execution data
   - Conforms to universal Wizard Structure Schema
   - Contains selectors, interactions, page structure
   - Used internally by FederalRunner for execution

2. **User Data Schema** - JSON Schema defining required inputs
   - Standard JSON Schema (draft-07)
   - Defines what users must provide
   - Used by Claude for data collection and validation

### 2. The field_id Link

The `field_id` in Wizard Data matches the property name in User Data Schema:

```
User Data Schema:      Wizard Data:
"birth_month" → {      field_id: "birth_month"
  type: "string",      selector: "#fsa_Input_DateOfBirthMonth"
  pattern: "..."       interaction: "fill"
}                      }
```

This simple link enables:
- Schema validation before execution
- Automatic mapping from user data to selectors
- Type-safe field resolution

### 3. Separation of Concerns

**Wizard Data** = Implementation detail (how to execute with Playwright)
**User Data Schema** = Public contract (what data users provide)

This separation enables:
- Schema can be used by other systems (API docs, form builders)
- Wizard data can change (re-discovery) without breaking schema
- Clear API between discovery and execution

---

## Requirements

### REQ-CONTRACT-001: Universal Wizard Structure Schema

**Requirement:** Define a universal JSON Schema that ALL discovered wizards must conform to.

**Location:** `schemas/wizard-structure-v1.schema.json`

**Purpose:**
- Ensures all wizard data files have consistent structure
- Enables FederalRunner to execute any wizard without code changes
- Provides validation during discovery and execution
- Version-controlled (v1, v2, etc. as format evolves)

**Structure:**
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "$id": "https://formflow.io/schemas/wizard-structure-v1.json",
  "title": "Wizard Structure Schema",
  "description": "Universal schema for discovered government form wizards",
  "version": "1.0.0",
  "type": "object",
  "required": ["wizard_id", "wizard_name", "url", "pages", "discovered_at"],
  "properties": {
    "wizard_id": {
      "type": "string",
      "pattern": "^[a-z0-9-]+$",
      "description": "Unique identifier (kebab-case)"
    },
    "wizard_name": {
      "type": "string",
      "description": "Human-readable name"
    },
    "url": {
      "type": "string",
      "format": "uri"
    },
    "start_action": {
      "type": "object",
      "properties": {
        "selector": {"type": "string"},
        "interaction": {
          "type": "string",
          "enum": ["click", "javascript_click"]
        }
      }
    },
    "pages": {
      "type": "array",
      "minItems": 1,
      "items": {
        "type": "object",
        "required": ["page_number", "fields", "continue_button"],
        "properties": {
          "page_number": {"type": "integer", "minimum": 1},
          "page_title": {"type": "string"},
          "fields": {
            "type": "array",
            "items": {
              "type": "object",
              "required": ["field_id", "selector", "interaction"],
              "properties": {
                "field_id": {
                  "type": "string",
                  "pattern": "^[a-z_][a-z0-9_]*$",
                  "description": "Links to user data schema property"
                },
                "label": {"type": "string"},
                "selector": {"type": "string"},
                "interaction": {
                  "type": "string",
                  "enum": ["fill", "click", "javascript_click", "fill_enter", "select"]
                },
                "field_type": {
                  "type": "string",
                  "enum": ["text", "number", "radio", "checkbox", "select", "typeahead"]
                },
                "required": {"type": "boolean"},
                "options": {"type": "array"}
              }
            }
          },
          "continue_button": {
            "type": "object",
            "required": ["selector", "interaction"]
          }
        }
      }
    },
    "discovered_at": {
      "type": "string",
      "format": "date-time"
    },
    "discovery_version": {"type": "string"}
  }
}
```

**Validation Points:**
1. **During discovery:** `federalscout_complete_discovery()` validates wizard data before saving
2. **During execution:** FederalRunner validates wizard data when loading
3. **During development:** Tests validate example wizard data

---

### REQ-CONTRACT-002: Wizard Data Generation (FederalScout)

**Requirement:** FederalScout must generate wizard data that conforms to universal schema.

**Tool:** `federalscout_complete_discovery()`

**Process:**
1. Build wizard structure from discovered pages (Pydantic validation)
2. Export to JSON
3. Validate against `schemas/wizard-structure-v1.schema.json`
4. Save to `wizards/wizard-data/{wizard_id}.json`

**Implementation:**
```python
# In federalscout_complete_discovery()

# 1. Build structure (existing Pydantic validation)
wizard_structure = WizardStructure(
    wizard_id=wizard_id,
    wizard_name=wizard_name,
    url=session.url,
    pages=session.pages_discovered,
    discovered_at=datetime.now(),
    discovery_version="1.0"
)

# 2. Export to JSON
wizard_json = wizard_structure.model_dump(mode='json')

# 3. NEW: Validate against universal schema
universal_schema = load_json('schemas/wizard-structure-v1.schema.json')
try:
    validate(wizard_json, universal_schema)
    logger.info("✅ Wizard structure validated against universal schema")
except ValidationError as e:
    logger.error(f"❌ Validation failed: {e}")
    return {'success': False, 'error': str(e)}

# 4. Save
save_json(f'wizards/wizard-data/{wizard_id}.json', wizard_json)
```

**No changes to agent instructions** - Pydantic models already enforce structure during page saves.

---

### REQ-CONTRACT-003: User Data Schema Generation (FederalScout)

**Requirement:** Claude must generate User Data Schema from wizard data.

**Tool:** `federalscout_save_schema()` (NEW)

**Input:**
- `wizard_id`: Identifier (e.g., "fsa-student-aid-estimator")
- `schema_content`: JSON Schema generated by Claude

**Process:**
1. Validate schema_content is valid JSON Schema (draft-07)
2. Check required fields: `$schema`, `type`, `properties`
3. Validate field names match wizard field_ids (optional warning)
4. Save to `wizards/wizard-schemas/{wizard_id}-schema.json`

**Implementation:**
```python
async def federalscout_save_schema(
    wizard_id: str,
    schema_content: dict
) -> dict:
    """
    Save Claude-generated User Data Schema.

    Claude generates this schema by analyzing wizard data.
    This tool validates and saves it.
    """

    # 1. Validate it's a valid JSON Schema
    try:
        # Check required fields
        if '$schema' not in schema_content:
            return {'success': False, 'error': 'Missing $schema field'}
        if 'type' not in schema_content:
            return {'success': False, 'error': 'Missing type field'}
        if 'properties' not in schema_content:
            return {'success': False, 'error': 'Missing properties field'}

        # Validate against JSON Schema meta-schema
        from jsonschema import Draft7Validator
        Draft7Validator.check_schema(schema_content)

    except Exception as e:
        return {
            'success': False,
            'error': f'Invalid JSON Schema: {str(e)}',
            'error_type': 'schema_validation_error'
        }

    # 2. Save to wizard-schemas/
    schema_path = config.wizards_dir / "wizard-schemas" / f"{wizard_id}-schema.json"
    schema_path.parent.mkdir(parents=True, exist_ok=True)

    save_json(schema_path, schema_content)

    logger.info(f"✅ Schema saved: {schema_path}")

    return {
        'success': True,
        'schema_path': str(schema_path),
        'validated': True,
        'message': 'Schema validated and saved successfully'
    }
```

---

### REQ-CONTRACT-004: Schema Generation Instructions (FederalScout Agent)

**Requirement:** Update FederalScout agent instructions to generate User Data Schema.

**File:** `agents/federalscout-instructions.md`

**New section after `federalscout_complete_discovery()`:**

```markdown
## After Discovery: Generate User Data Schema

After `federalscout_complete_discovery()` succeeds, you MUST:

1. **Create Wizard Data Artifact**
   - Title: "{Wizard Name} - Complete Wizard Structure"
   - Content: Full `wizard_data` JSON from tool response
   - Format: Markdown code block (```json)

2. **Generate User Data Schema**

   Analyze the wizard data and create a JSON Schema (draft-07) that defines:

   - **Property names**: Use `field_id` from wizard fields
   - **Types**: Map wizard field_type to JSON Schema types:
     - `text` → `"type": "string"`
     - `number` → `"type": "integer"` or `"string"` with pattern
     - `radio` → `"type": "string", "enum": [options]`
     - `select` → `"type": "string", "enum": [options]`
     - `typeahead` → `"type": "string"`
     - `checkbox` → `"type": "boolean"`

   - **Validation patterns**: Add regex patterns:
     - Month: `"^(0[1-9]|1[0-2])$"`
     - Day: `"^(0[1-9]|[12][0-9]|3[01])$"`
     - Year: `"^[12][0-9]{3}$"`
     - Currency: `"type": "integer", "minimum": 0`

   - **Descriptions**: Use field labels
   - **Examples**: Use example_value if available
   - **Required fields**: List all required field_ids

3. **Create Schema Artifact**
   - Title: "{Wizard Name} - User Data Schema"
   - Content: Generated JSON Schema
   - Format: Markdown code block (```json)

4. **Save Schema**
   - Call: `federalscout_save_schema(wizard_id, schema_content)`
   - Tool will validate and save to `wizard-schemas/`

Example schema structure:
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "$id": "https://formflow.io/schemas/{wizard_id}.json",
  "title": "{Wizard Name} Input Schema",
  "description": "User data required to execute {wizard_name}",
  "version": "1.0.0",
  "discoveredAt": "{timestamp}",
  "sourceUrl": "{wizard_url}",
  "type": "object",
  "required": ["field_id_1", "field_id_2", ...],
  "properties": {
    "field_id_1": {
      "type": "string",
      "pattern": "...",
      "description": "...",
      "examples": ["..."]
    }
  }
}
```
```

---

### REQ-CONTRACT-005: Schema Loading (FederalRunner)

**Requirement:** FederalRunner must load and return User Data Schema.

**Tool:** `federalrunner_get_wizard_info()` (UPDATED)

**Changes:**
- OLD: Return complete wizard structure
- NEW: Return User Data Schema + basic wizard info

**Implementation:**
```python
async def federalrunner_get_wizard_info(wizard_id: str) -> dict:
    """
    Get wizard information including User Data Schema.

    Returns the schema so Claude knows what data to collect.
    """

    # 1. Load wizard data (for metadata)
    wizard_path = config.wizards_dir / "wizard-data" / f"{wizard_id}.json"
    if not wizard_path.exists():
        return {'success': False, 'error': 'Wizard not found'}

    wizard_data = load_json(wizard_path)

    # 2. Load User Data Schema (THE CONTRACT)
    schema_path = config.wizards_dir / "wizard-schemas" / f"{wizard_id}-schema.json"
    if not schema_path.exists():
        return {'success': False, 'error': 'Schema not found for this wizard'}

    schema = load_json(schema_path)

    # 3. Return schema + basic info
    return {
        'success': True,
        'wizard_id': wizard_id,
        'name': wizard_data['wizard_name'],
        'url': wizard_data['url'],
        'total_pages': len(wizard_data['pages']),
        'schema': schema  # ← Claude reads this to collect user data
    }
```

---

### REQ-CONTRACT-006: User Data Validation (FederalRunner)

**Requirement:** FederalRunner must validate user_data against User Data Schema before execution.

**Tool:** `federalrunner_execute_wizard()` (UPDATED)

**Implementation:**
```python
async def federalrunner_execute_wizard(wizard_id: str, user_data: dict) -> dict:
    """
    Execute wizard with user data.

    Validates user_data against schema first.
    """

    # 1. Load User Data Schema
    schema_path = config.wizards_dir / "wizard-schemas" / f"{wizard_id}-schema.json"
    schema = load_json(schema_path)

    # 2. Validate user_data
    from jsonschema import validate, ValidationError
    try:
        validate(user_data, schema)
    except ValidationError as e:
        return {
            'success': False,
            'error': 'User data validation failed',
            'validation_errors': str(e),
            'missing_fields': extract_missing_fields(e),
            'invalid_fields': extract_invalid_fields(e)
        }

    # 3. Load wizard data
    wizard_path = config.wizards_dir / "wizard-data" / f"{wizard_id}.json"
    wizard_data = load_json(wizard_path)

    # 4. Map user_data to wizard fields via field_id
    field_values = {}
    for page in wizard_data['pages']:
        for field in page['fields']:
            field_id = field['field_id']
            if field_id in user_data:
                field_values[field['selector']] = user_data[field_id]

    # 5. Execute with Playwright (atomic)
    results = await execute_wizard_atomically(wizard_data, field_values)

    return results
```

---

### REQ-CONTRACT-007: FederalRunner Agent Instructions

**Requirement:** Update FederalRunner agent instructions to use schema-first approach.

**File:** `agents/federalrunner-instructions.md`

**Key sections:**

```markdown
## Execution Workflow

1. **List Available Wizards**
   - Call: `federalrunner_list_wizards()`
   - Identify relevant wizard for user's request

2. **Get Wizard Schema**
   - Call: `federalrunner_get_wizard_info(wizard_id)`
   - Receives User Data Schema
   - Schema tells you what data to collect from user

3. **Collect User Data**

   Read the schema's `properties` to understand required fields:
   - Property names (e.g., "birth_month")
   - Types (string, integer, etc.)
   - Validation rules (patterns, enums, ranges)
   - Descriptions (help text)

   Transform user's natural language into schema-compliant data:
   - "born in May 2007" → birth_month: "05", birth_year: "2007"
   - "$120,000 income" → parent_income: 120000
   - "single" → marital_status: "unmarried"

   Use your intelligence to:
   - Extract data from rich context
   - Handle synonyms and variations
   - Convert formats (currency, dates)
   - Infer missing data when reasonable

4. **Execute Wizard**
   - Call: `federalrunner_execute_wizard(wizard_id, user_data)`
   - If validation errors: Ask user for missing/corrected data
   - If success: Present results with screenshots

## No Field Mapper Needed

The schema IS your field mapper! You read the schema and collect data accordingly.

Example:
```json
// Schema says:
{
  "birth_month": {
    "type": "string",
    "pattern": "^(0[1-9]|1[0-2])$",
    "description": "Month (01-12)"
  }
}

// User says: "born in May"
// You extract: birth_month = "05"
```
```

---

## Implementation Phases

### Phase 1: FederalScout Schema Generation ✅ **DO THIS FIRST**

**Goal:** Get FederalScout generating both artifacts and test in Claude Desktop.

**Tasks:**

1. **Create universal schema**
   - File: `schemas/wizard-structure-v1.schema.json`
   - Define complete structure (see REQ-CONTRACT-001)
   - Add validation to `federalscout_complete_discovery()`

2. **Create `federalscout_save_schema()` tool**
   - File: `mcp-servers/federalscout-mcp/src/discovery_tools.py`
   - Implement validation (see REQ-CONTRACT-003)
   - Save to `wizards/wizard-schemas/`

3. **Create wizard-schemas/ directory**
   - `mkdir -p wizards/wizard-schemas`
   - Update `.gitignore` (track both wizard-data and wizard-schemas)

4. **Update agent instructions**
   - File: `agents/federalscout-instructions.md`
   - Add schema generation section (see REQ-CONTRACT-004)
   - Include field type mapping table
   - Include validation pattern examples

5. **Write tests**
   - File: `tests/test_schema_generation.py`
   - Test `federalscout_save_schema()` validation
   - Test schema file creation
   - Test invalid schema handling

6. **Test in Claude Desktop**
   - Complete FSA discovery (already done)
   - Verify Claude generates schema artifact
   - Verify `federalscout_save_schema()` called successfully
   - Verify schema file created: `wizards/wizard-schemas/fsa-student-aid-estimator-schema.json`
   - Validate schema is well-formed JSON Schema (draft-07)

**Success Criteria:**
- ✅ Universal schema exists and validates FSA wizard data
- ✅ `federalscout_save_schema()` tool works
- ✅ Agent generates valid User Data Schema for FSA
- ✅ Both artifacts (wizard-data + wizard-schema) created

---

### Phase 2: FederalRunner Schema Consumption

**Goal:** Get FederalRunner loading and using schemas (AFTER FederalScout complete).

**Tasks:**

1. **Update `federalrunner_get_wizard_info()`**
   - Load schema from `wizard-schemas/`
   - Return schema in response (see REQ-CONTRACT-005)
   - Test with pytest

2. **Update `federalrunner_execute_wizard()`**
   - Add schema validation (see REQ-CONTRACT-006)
   - Map user_data to fields via field_id
   - Test with pytest

3. **Remove field_mapper.py**
   - Delete file (Claude does this now)
   - Remove imports
   - Update tests

4. **Update agent instructions**
   - File: `agents/federalrunner-instructions.md`
   - Add schema-first workflow (see REQ-CONTRACT-007)
   - Include examples of data extraction

5. **Write tests**
   - Test schema loading
   - Test validation (valid and invalid data)
   - Test field_id mapping to selectors

6. **Test locally with pytest**
   - Non-headless first (Chromium, visible browser)
   - Headless second (WebKit, production mode)

7. **Test with Claude Desktop**
   - Local MCP server
   - Full execution flow with schema

**Success Criteria:**
- ✅ FederalRunner loads and returns schema
- ✅ User data validated before execution
- ✅ field_id correctly maps to selectors
- ✅ Execution works end-to-end

---

## Benefits

### 1. Claude as Intelligent Data Collector

No hardcoded field mappers. Claude reads schema and collects data naturally:

```
User: "I'm 17, born May 2007, from Illinois, income $120k"

Claude (reads schema):
  - birth_month: pattern "^(0[1-9]|1[0-2])$" → "05"
  - birth_year: pattern "^[12][0-9]{3}$" → "2007"
  - state: enum [all states] → "Illinois"
  - parent_income: integer, min 0 → 120000

Claude: "I have birth_month='05', birth_year='2007', state='Illinois',
         parent_income=120000. I still need birth_day and marital_status."
```

### 2. Type Safety & Validation

```python
# Validate BEFORE execution
validate(user_data, schema)

# Catch errors early:
# - Missing required fields
# - Wrong types (string vs integer)
# - Pattern mismatches (invalid month "13")
# - Out of range values
```

### 3. Universal Design

Same tools work for ANY wizard:

```
FederalScout discovers:
  - FSA Student Aid Estimator → generates schema
  - SSA Retirement Estimator → generates schema
  - IRS Withholding Calculator → generates schema

FederalRunner executes all three with ZERO code changes:
  - Load schema (different for each)
  - Validate user_data (schema-specific validation)
  - Execute (universal Playwright logic)
```

### 4. Self-Documenting

User Data Schema serves as:
- API contract (what data to provide)
- Documentation (field descriptions)
- Validation rules (runtime enforcement)
- Test specification (what data is valid)

### 5. Portable and Reusable

Standard JSON Schema enables:
- Other systems can consume (API docs, form builders)
- Schema registry/catalog possible
- Version control and evolution (v1, v2)
- Automated documentation generation

---

## Blog Content

### Title Options:
- "Contract-First Form Automation: Turning Forms into Type-Safe APIs"
- "From Pixels to Schemas: How Claude Vision Automates Government Forms"
- "Self-Describing Wizards: A Universal Pattern for Form Automation"

### Key Messages:

1. **The Problem**
   - Government forms are visual, not APIs
   - No programmatic access to FSA, SSA, IRS calculators
   - Traditional approaches: brittle screen scraping + hardcoded mappings

2. **The Solution**
   - Vision-guided discovery (Claude + Playwright)
   - Automatic schema generation (Claude's intelligence)
   - Contract-first execution (type-safe validation)

3. **The Innovation**
   - Forms describe themselves (User Data Schema)
   - Claude reads schema and collects data naturally
   - Universal tools work with ANY form

4. **The Demo**
   - Voice interaction on mobile: "I'm 17, from Illinois..."
   - Claude extracts data according to schema
   - Official FSA results in 8 seconds
   - Transparent audit trail (screenshots)

### Demo Script:

```
[Scene: College campus tour, Samsung Galaxy Fold 7]

User (voice): "Hey Claude, I just finished touring Northwestern and need
               to figure out if we can afford it. Can you calculate my
               federal student aid? I'm 17, born in May 2007, single,
               from Illinois, and I'll be a freshman in fall 2026. My
               parents are married, also in Illinois, family of four -
               me, my parents, and my little brother. Income last year
               was $120,000, we have about $30,000 in savings, no child
               support, and I didn't have any income. Northwestern costs
               like $85,000 a year."

Claude: "I'll calculate your federal student aid using the official FSA
         Estimator. One moment..."

         [Calls federalrunner_execute_wizard with extracted data]
         [8 seconds pass]

         "Your Student Aid Index (SAI) is $19,514. This means your family
         is expected to contribute $19,514 toward college costs.

         With Northwestern's $85,000 annual cost, you'd need approximately
         $65,486 in financial aid. You are eligible for federal aid and
         estimated Pell Grant of $3,500.

         This is the official calculation from studentaid.gov."

         [Shows screenshots from all 7 pages]

[Key moment: Rich context provided upfront, instant official results]
```

---

## Success Criteria

### FederalScout Phase:
✅ Universal Wizard Structure Schema exists
✅ `federalscout_save_schema()` tool implemented
✅ Agent generates valid User Data Schemas
✅ Both artifacts created for FSA wizard
✅ Schema conforms to JSON Schema draft-07
✅ Tested in Claude Desktop

### FederalRunner Phase:
✅ `federalrunner_get_wizard_info()` returns schema
✅ `federalrunner_execute_wizard()` validates against schema
✅ field_id correctly maps user_data to wizard selectors
✅ field_mapper.py removed (Claude does data mapping)
✅ Pytest tests pass (non-headless + headless)
✅ Claude Desktop integration works
✅ End-to-end execution successful

---

## Technical References

- JSON Schema Specification: https://json-schema.org/draft-07/schema
- JSON Schema Validation: https://python-jsonschema.readthedocs.io/
- Pydantic JSON Schema: https://docs.pydantic.dev/latest/concepts/json_schema/

---

**Next Steps:**
1. Create `schemas/wizard-structure-v1.schema.json`
2. Implement `federalscout_save_schema()` tool
3. Update FederalScout agent instructions
4. Test schema generation in Claude Desktop
5. THEN move to FederalRunner implementation
