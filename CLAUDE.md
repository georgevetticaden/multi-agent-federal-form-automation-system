# Multi-Agent Federal Form Automation System - Implementation Guide for Claude Code

## Project Overview

Multi-Agent Federal Form Automation System enables automation of government form wizards through **Contract-First Form Automation** - a pattern where visual form discovery automatically generates type-safe contracts (JSON Schemas) that bridge human interaction and automated execution.

**Two specialized agents:**
1. **FederalScout** - Discovers wizard structures + generates schemas (local, Claude Desktop) 🚧 **SCHEMA GENERATION IN PROGRESS**
2. **FederalRunner** - Executes wizards with validated user data (cloud, atomic) ⬜ **NOT STARTED**

This guide directs Claude Code through systematic implementation from discovery to production deployment.

---

## Architecture: Contract-First Form Automation

### The Pattern

```
Discovery → Structure + Contract → Type-Safe Execution

FederalScout discovers forms and generates TWO artifacts:
1. Wizard Data (Playwright execution instructions)
2. User Data Schema (JSON Schema contract)

FederalRunner reads the schema and executes:
1. Claude collects user data (reads schema to know what to ask)
2. FederalRunner validates (against schema)
3. FederalRunner executes (maps via field_id to selectors)
```

**Complete pattern documentation:** `requirements/shared/CONTRACT_FIRST_FORM_AUTOMATION.md`

### Three-Layer Schema Architecture

```
┌──────────────────────────────────────────┐
│  Universal Wizard Structure Schema (v1)  │  ← Defines what ALL wizards must look like
│  schemas/wizard-structure-v1.schema.json │     for Playwright execution
└──────────────────────────────────────────┘
              ↓ conformsTo
┌──────────────────────────────────────────┐
│  Wizard Data (per wizard)                │  ← Specific discovered wizard
│  wizards/wizard-data/                    │     (FSA, SSA, IRS, etc.)
│    fsa-student-aid-estimator.json        │
└──────────────────────────────────────────┘
              ↓ generates (via Claude)
┌──────────────────────────────────────────┐
│  User Data Schema (per wizard)           │  ← THE CONTRACT
│  wizards/wizard-schemas/                 │     What user data is required
│    fsa-student-aid-estimator-schema.json │
└──────────────────────────────────────────┘
```

**Key Link:** `field_id` in Wizard Data matches property name in User Data Schema

```
User Data Schema:           Wizard Data:
"birth_month" → {          field_id: "birth_month"
  type: "string",          selector: "#fsa_Input_DateOfBirthMonth"
  pattern: "..."           interaction: "fill"
}                          }
```

### Why This Matters

**Traditional approach:**
- Discover form → Hardcode field mappings → Maintain code for each form

**Contract-First approach:**
- Discover form → Generate schema (Claude's intelligence) → Universal execution
- No field_mapper.py needed - Claude reads schema and collects data naturally
- Same tools work for FSA, Social Security, IRS calculators (zero code changes)

---

## ✅ COMPLETED: Phases 1-3 (FederalScout Discovery)

### Phase 1: Shared Foundation ✅
- ✅ Wizard structure models (`models.py`) with Pydantic
- ✅ JSON schema validation
- ✅ Configuration management via environment variables
- ✅ DateTime serialization handling (mode='json')
- ✅ Shared wizards directory (`multi-agent-federal-form-automation-system/wizards/`)

### Phase 2: FederalScout Discovery Agent ✅
- ✅ MCP stdio server for Claude Desktop
- ✅ Playwright client with session management
- ✅ All 6 discovery tools implemented:
  1. `federalscout_start_discovery` - Begin session
  2. `federalscout_click_element` - Navigate pages
  3. `federalscout_execute_actions` - Universal batch actions (fills, clicks, selects)
  4. `federalscout_get_page_info` - Extract elements (no screenshot)
  5. `federalscout_save_page_metadata` - Save pages with incremental backup
  6. `federalscout_complete_discovery` - Finalize and return complete JSON
- ✅ Screenshot optimization (42-52KB, quality=60, viewport-only)
- ✅ Intelligent zoom + dynamic viewport resize
- ✅ Session persistence and timeout handling
- ✅ Incremental saves (partial wizard files)
- ✅ Structured logging to file
- ✅ Agent instructions with checkpoint system

**Critical patterns implemented:**
- ✅ Hidden radio buttons → `javascript_click`
- ✅ Typeahead fields → `fill_enter` (fill + Enter key)
- ✅ Conditional fields → Sequential filling with screenshot validation
- ✅ Universal batch actions → 70-83% conversation size reduction
- ✅ MCP ImageContent format → 50-70% size reduction
- ✅ Checkpoint system → Pause after page 4 for long wizards

### Phase 3: FSA Wizard Discovery ✅
- ✅ Complete FSA Student Aid Estimator discovery via Claude Desktop
- ✅ Output: `wizards/wizard-data/fsa-student-aid-estimator.json`
- ✅ 7 pages, 17 fields fully mapped
- ✅ All selectors tested and validated
- ✅ Interaction types documented (fill, javascript_click, fill_enter)
- ✅ Conforms to Wizard Structure Schema

**Page breakdown:**
- Page 1: Student Information (6 fields)
- Page 2: Student Personal Circumstances (2 fields)
- Page 3: Parent Marital Status (1 field)
- Page 4: Parent Information (2 fields)
- Page 5: Family Size (1 field)
- Page 6: Parent Income and Assets (4 fields)
- Page 7: Student Income and Assets (1 field)

---

## 🚧 IN PROGRESS: Phase 3.5 - Contract-First Schema Generation

**Goal:** Complete FederalScout implementation by adding schema generation capability.

**Reference:** `requirements/shared/CONTRACT_FIRST_FORM_AUTOMATION.md`

**Status:** Ready to implement

### Why This Phase

Transform FederalScout from discovery-only to **discovery + contract generation**:
- Wizard Data → What FederalScout discovered (Playwright execution data)
- **User Data Schema** → What users must provide (THE CONTRACT) ← NEW

**Result:** FederalRunner doesn't need field_mapper.py - Claude reads the schema!

### Implementation Tasks

#### Task 1: Create Universal Wizard Structure Schema

**File:** `schemas/wizard-structure-v1.schema.json`

**Purpose:** Define what ALL wizard data files must conform to (universal validation)

**Reference:** CONTRACT_FIRST_FORM_AUTOMATION.md REQ-CONTRACT-001

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
    "wizard_id": {"type": "string", "pattern": "^[a-z0-9-]+$"},
    "wizard_name": {"type": "string"},
    "url": {"type": "string", "format": "uri"},
    "start_action": {...},
    "pages": {
      "type": "array",
      "items": {
        "required": ["page_number", "fields", "continue_button"],
        "properties": {
          "page_number": {"type": "integer"},
          "fields": {
            "type": "array",
            "items": {
              "required": ["field_id", "selector", "interaction"],
              "properties": {
                "field_id": {
                  "type": "string",
                  "pattern": "^[a-z_][a-z0-9_]*$",
                  "description": "Links to user data schema property"
                },
                "selector": {"type": "string"},
                "interaction": {
                  "type": "string",
                  "enum": ["fill", "click", "javascript_click", "fill_enter", "select"]
                },
                "field_type": {...},
                "required": {"type": "boolean"}
              }
            }
          }
        }
      }
    }
  }
}
```

**Tasks:**
- [ ] Create `schemas/` directory
- [ ] Create `wizard-structure-v1.schema.json` with complete definition
- [ ] Add JSON Schema validation to `federalscout_complete_discovery()`
- [ ] Test validation with existing FSA wizard data

---

#### Task 2: Implement federalscout_save_schema() Tool

**File:** `mcp-servers/federalscout-mcp/src/discovery_tools.py`

**Purpose:** Save Claude-generated User Data Schema

**Reference:** CONTRACT_FIRST_FORM_AUTOMATION.md REQ-CONTRACT-003

**Implementation:**
```python
async def federalscout_save_schema(
    wizard_id: str,
    schema_content: dict
) -> dict:
    """
    Save Claude-generated User Data Schema.

    Claude generates this by analyzing wizard data.
    This tool validates and saves it.

    Args:
        wizard_id: e.g., "fsa-student-aid-estimator"
        schema_content: JSON Schema (draft-07) generated by Claude

    Returns:
        {
            'success': True,
            'schema_path': 'wizards/wizard-schemas/fsa-...-schema.json',
            'validated': True
        }
    """

    # 1. Validate it's a valid JSON Schema (draft-07)
    from jsonschema import Draft7Validator

    if '$schema' not in schema_content:
        return {'success': False, 'error': 'Missing $schema field'}

    try:
        Draft7Validator.check_schema(schema_content)
    except Exception as e:
        return {'success': False, 'error': f'Invalid JSON Schema: {str(e)}'}

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

**Tasks:**
- [ ] Add `federalscout_save_schema()` to discovery_tools.py
- [ ] Add `jsonschema` to requirements.txt
- [ ] Create `wizards/wizard-schemas/` directory
- [ ] Update .gitignore to track wizard-schemas/
- [ ] Write unit tests for validation

---

#### Task 3: Update FederalScout Agent Instructions

**File:** `agents/federalscout-instructions.md`

**Reference:** CONTRACT_FIRST_FORM_AUTOMATION.md REQ-CONTRACT-004

**Add new section after discovery completes:**

```markdown
## After Discovery: Generate User Data Schema

After `federalscout_complete_discovery()` succeeds, you MUST generate a User Data Schema.

### Step 1: Create Wizard Data Artifact

Create a markdown code block with the complete wizard structure:
- Title: "{Wizard Name} - Complete Wizard Structure"
- Content: Full `wizard_data` JSON from tool response
- Format: ```json ... ```

### Step 2: Generate User Data Schema

Analyze the wizard data and create a JSON Schema (draft-07):

**Field Type Mapping:**
| Wizard field_type | JSON Schema type | Validation |
|-------------------|------------------|------------|
| text | string | minLength, maxLength |
| number | integer or string | minimum/maximum or pattern |
| radio | string | enum (list all options) |
| select | string | enum (from <option> values) |
| typeahead | string | (optional enum) |
| checkbox | boolean | - |

**Validation Patterns:**
- Month: `"^(0[1-9]|1[0-2])$"`
- Day: `"^(0[1-9]|[12][0-9]|3[01])$"`
- Year: `"^[12][0-9]{3}$"`
- Income: `"type": "integer", "minimum": 0`

**Schema Structure:**
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
  "required": [list all required field_ids],
  "properties": {
    "{field_id}": {  // ← MUST match field_id from wizard data
      "type": "...",
      "pattern": "...",
      "description": "{field label}",
      "examples": ["{example_value}"]
    }
  }
}
```

### Step 3: Create Schema Artifact

Create a markdown code block with the generated schema:
- Title: "{Wizard Name} - User Data Schema (THE CONTRACT)"
- Content: Complete JSON Schema
- Format: ```json ... ```

### Step 4: Save Schema

Call: `federalscout_save_schema(wizard_id, schema_content)`

This validates and saves the schema to `wizards/wizard-schemas/`.
```

**Tasks:**
- [ ] Update federalscout-instructions.md
- [ ] Add field type mapping table
- [ ] Add validation pattern examples
- [ ] Add complete workflow example

---

#### Task 4: Write Tests

**File:** `mcp-servers/federalscout-mcp/tests/test_schema_generation.py`

**Tests:**
```python
@pytest.mark.asyncio
async def test_save_schema_valid():
    """Test saving a valid JSON Schema."""
    schema = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "title": "Test Schema",
        "type": "object",
        "properties": {
            "birth_month": {
                "type": "string",
                "pattern": "^(0[1-9]|1[0-2])$"
            }
        }
    }

    result = await federalscout_save_schema("test-wizard", schema)

    assert result['success'] is True
    assert result['validated'] is True
    assert Path(result['schema_path']).exists()

@pytest.mark.asyncio
async def test_save_schema_invalid():
    """Test saving an invalid schema."""
    schema = {"invalid": "schema"}  # Missing required fields

    result = await federalscout_save_schema("test-wizard", schema)

    assert result['success'] is False
    assert 'error' in result

@pytest.mark.asyncio
async def test_complete_discovery_validates_against_universal_schema():
    """Test that wizard data validates against universal schema."""
    # ... build wizard structure ...
    result = await federalscout_complete_discovery(...)

    assert result['success'] is True

    # Load saved wizard data
    wizard_data = load_json(result['wizard_data_path'])

    # Validate against universal schema
    universal_schema = load_json('schemas/wizard-structure-v1.schema.json')
    validate(wizard_data, universal_schema)  # Should not raise
```

**Tasks:**
- [ ] Create test_schema_generation.py
- [ ] Test valid schema saving
- [ ] Test invalid schema handling
- [ ] Test universal schema validation
- [ ] Test directory creation

---

#### Task 5: Test in Claude Desktop

**Goal:** Complete FSA discovery + schema generation end-to-end

**Steps:**

1. **Configure Claude Desktop** (if not already):
```json
{
  "mcpServers": {
    "federalscout": {
      "command": "python",
      "args": ["-m", "federalscout_mcp.server"],
      "cwd": "/path/to/mcp-servers/federalscout-mcp"
    }
  }
}
```

2. **Test conversation:**
```
YOU: I want to re-discover the FSA Student Aid Estimator to generate
     the user data schema.

CLAUDE: [Calls federalscout_start_discovery]
        [Discovers all 7 pages]
        [Calls federalscout_complete_discovery]

        Here's the complete wizard structure:
        [Shows wizard data artifact]

        Now let me generate the User Data Schema:
        [Shows schema artifact with field mappings]

        [Calls federalscout_save_schema]

        ✅ Schema saved to: wizards/wizard-schemas/fsa-student-aid-estimator-schema.json
```

3. **Verify outputs:**
- [ ] `wizards/wizard-data/fsa-student-aid-estimator.json` exists
- [ ] `wizards/wizard-schemas/fsa-student-aid-estimator-schema.json` exists
- [ ] Schema is valid JSON Schema (draft-07)
- [ ] Schema properties match wizard field_ids
- [ ] Schema includes validation patterns

---

### Success Criteria - Phase 3.5

✅ Universal Wizard Structure Schema created
✅ `federalscout_save_schema()` tool implemented
✅ Agent instructions updated with schema generation workflow
✅ Tests pass (validation, saving, error handling)
✅ Claude Desktop test: Both artifacts created for FSA
✅ Schema conforms to JSON Schema draft-07
✅ Schema field names match wizard field_ids

**STOP HERE - DO NOT PROCEED TO FEDERALRUNNER UNTIL FEDERALSCOUT SCHEMA GENERATION IS COMPLETE AND TESTED**

---

## ⬜ NOT STARTED: Phase 4 (FederalRunner Execution Agent)

**Status:** Will begin AFTER Phase 3.5 complete

**Goal:** Execute wizards using Contract-First pattern

**Reference:** `requirements/shared/CONTRACT_FIRST_FORM_AUTOMATION.md` Phase 2

### Overview

FederalRunner uses the schema-first approach:
1. Load User Data Schema (from wizard-schemas/)
2. Return schema to Claude (Claude collects user data)
3. Validate user_data against schema (before execution)
4. Load Wizard Data (from wizard-data/)
5. Map user_data to selectors via field_id
6. Execute atomically with Playwright

**No field_mapper.py needed** - Claude reads schema and collects data naturally!

### Browser Strategy

**CRITICAL:** FSA website blocks headless Chromium/Firefox. Use WebKit for headless.

| Environment | Headless | Browser | Purpose |
|-------------|----------|---------|---------|
| Local pytest (FIRST) | False | Chromium | Visual debugging |
| Local pytest (SECOND) | True | WebKit | Production validation |
| Local MCP (Claude Desktop) | False | Chromium | Interactive testing |
| Cloud Run (Production) | True | WebKit | Deployment |

### Implementation Steps (High-Level)

Will be detailed AFTER Phase 3.5 complete.

**Step 1:** Core infrastructure
- Copy models.py from FederalScout
- Create config.py, logging_config.py
- Create requirements.txt

**Step 2:** Playwright execution client
- Atomic execution pattern (launch → fill → extract → close)
- Field execution logic (fill, click, fill_enter, select)
- Screenshot capture after each page

**Step 3:** Schema validator (REPLACES field_mapper.py)
- Load schema from wizard-schemas/
- Validate user_data with jsonschema library
- Map user_data to selectors via field_id

**Step 4:** Local pytest tests
- Non-headless first (Chromium, visible)
- Headless second (WebKit, production)
- Schema validation tests
- End-to-end execution tests

**Step 5:** MCP tools
- `federalrunner_list_wizards()` - List available wizards
- `federalrunner_get_wizard_info(wizard_id)` - Return schema (THE CONTRACT)
- `federalrunner_execute_wizard(wizard_id, user_data)` - Validate + execute

**Step 6:** FastAPI server (local HTTP)
- MCP protocol implementation
- Health check endpoint
- Local testing without OAuth

**Step 7:** Claude Desktop integration
- Test schema-first workflow locally
- Verify Claude collects data by reading schema
- Verify execution works end-to-end

---

## ⬜ NOT STARTED: Phase 5 (Cloud Deployment)

**Status:** Will begin AFTER Phase 4 complete

### Overview

Deploy FederalRunner to Google Cloud Run with OAuth 2.1 authentication.

**Reference:**
- `requirements/execution/EXECUTION_REQUIREMENTS.md` REQ-EXEC-011 through REQ-EXEC-015
- `requirements/shared/AUTHENTICATION_REQUIREMENTS.md`
- MDCalc reference: `requirements/reference/mdcalc/`

### Steps (High-Level)

**5.1 OAuth 2.1 Authentication**
- Auth0 API resource configuration
- JWT token validation (JWKS-based)
- Scope-based permissions (`federalrunner:read`, `federalrunner:execute`)

**5.2 Dockerfile**
- Multi-stage build
- Playwright + WebKit dependencies (NOT Chromium)
- Copy wizard files (both wizard-data and wizard-schemas)
- Environment: `FEDERALRUNNER_HEADLESS=true`, `BROWSER_TYPE=webkit`

**5.3 Cloud Run Deployment**
- 2 CPU, 2Gi memory, 60s timeout
- Environment variables configuration
- Health check endpoint

**5.4 Claude.ai Integration**
- Remote MCP server configuration
- Production testing from Claude.ai web
- Mobile app testing (Android/iOS)

**5.5 Voice Demo (Samsung Galaxy Fold 7)**
- "Three Moments" demo script
- Rich context upfront pattern
- Record video for blog

---

## Implementation Checklist

### ✅ Phase 1: Foundation (COMPLETE)
- ✅ Wizard structure models
- ✅ Configuration management
- ✅ Shared wizards directory

### ✅ Phase 2: FederalScout Discovery (COMPLETE)
- ✅ MCP stdio server
- ✅ Playwright client
- ✅ All 6 discovery tools
- ✅ Claude Desktop integration

### ✅ Phase 3: FSA Wizard Discovery (COMPLETE)
- ✅ `fsa-student-aid-estimator.json` created
- ✅ 7 pages, 17 fields mapped
- ✅ All selectors tested

### 🚧 Phase 3.5: Schema Generation (IN PROGRESS)
- [ ] Create `schemas/wizard-structure-v1.schema.json`
- [ ] Add universal schema validation to `federalscout_complete_discovery()`
- [ ] Implement `federalscout_save_schema()` tool
- [ ] Create `wizards/wizard-schemas/` directory
- [ ] Update FederalScout agent instructions
- [ ] Write schema generation tests
- [ ] Test in Claude Desktop (complete workflow)

### ⬜ Phase 4: FederalRunner Execution (NOT STARTED)
- [ ] Core infrastructure
- [ ] Playwright execution client
- [ ] Schema validator (no field_mapper.py)
- [ ] Local pytest tests (non-headless + headless)
- [ ] MCP tools (schema-first approach)
- [ ] FastAPI server
- [ ] Claude Desktop integration

### ⬜ Phase 5: Cloud Deployment (NOT STARTED)
- [ ] OAuth 2.1 authentication
- [ ] Dockerfile (WebKit for headless)
- [ ] Cloud Run deployment
- [ ] Claude.ai integration
- [ ] Voice demo recording

---

## Success Criteria

### ✅ Discovery Phase (COMPLETE)
1. ✅ FederalScout discovers FSA wizard successfully
2. ✅ `fsa-student-aid-estimator.json` validates
3. ✅ All selectors tested via Claude Desktop

### 🚧 Schema Generation Phase (IN PROGRESS)
4. ⏳ Universal Wizard Structure Schema created
5. ⏳ FederalScout generates User Data Schema for FSA
6. ⏳ Both artifacts (wizard-data + wizard-schemas) exist
7. ⏳ Schema is valid JSON Schema (draft-07)
8. ⏳ Schema field_ids match wizard field_ids

### ⬜ Execution Phase (NOT STARTED)
9. ⬜ FederalRunner loads and returns schema to Claude
10. ⬜ FederalRunner validates user_data before execution
11. ⬜ field_id correctly maps to selectors
12. ⬜ Pytest tests pass (non-headless + headless)
13. ⬜ Claude Desktop execution works

### ⬜ Deployment Phase (NOT STARTED)
14. ⬜ Cloud Run deployment successful
15. ⬜ OAuth authentication works
16. ⬜ Claude.ai execution works
17. ⬜ Mobile voice demo successful
18. ⬜ Universal design verified (ready for SSA, IRS forms)

---

## Critical Learnings to Apply

### From FederalScout Discovery ✅
- Hidden elements need JavaScript click
- Typeahead fields need Enter keypress
- Intelligent zoom + dynamic viewport resize
- Universal batch actions (70-83% size reduction)
- Checkpoint system for long wizards

### Contract-First Pattern 🆕
- **Schema is the contract** between agents
- **Claude collects data** by reading schema (no field_mapper.py)
- **field_id links** schema properties to wizard selectors
- **Universal design** - works with ANY wizard
- **Type safety** - validation before execution

### For FederalRunner (Future)
- Atomic execution (launch → fill → close)
- WebKit for headless (FSA compatibility)
- Schema validation before execution
- Screenshot audit trail
- Error recovery with helpful messages

---

## Next Steps

**Focus: Complete Phase 3.5 (Schema Generation)**

1. Create `schemas/wizard-structure-v1.schema.json`
2. Implement `federalscout_save_schema()` tool
3. Update FederalScout agent instructions
4. Write and run tests
5. Test end-to-end in Claude Desktop

**DO NOT proceed to FederalRunner until schema generation is complete and tested.**

---

## References

- **Contract-First Pattern:** `requirements/shared/CONTRACT_FIRST_FORM_AUTOMATION.md`
- **Wizard Structure Schema:** `requirements/shared/WIZARD_STRUCTURE_SCHEMA.md`
- **Execution Requirements:** `requirements/execution/EXECUTION_REQUIREMENTS.md`
- **JSON Schema Spec:** https://json-schema.org/draft-07/schema
- **Blog Demo Script:** `docs/blog-demo/federalrunner_demo_realistic.txt`
