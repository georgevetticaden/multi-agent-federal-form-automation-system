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

## ✅ COMPLETED: Phase 3.5 - Contract-First Schema Generation

**Goal:** Complete FederalScout implementation by adding schema generation capability.

**Reference:** `requirements/shared/CONTRACT_FIRST_FORM_AUTOMATION.md`

**Status:** ✅ COMPLETE

✅ FederalScout now generates both artifacts:
- Wizard Data → Playwright execution instructions
- **User Data Schema** → THE CONTRACT for user data collection

✅ Schema-first approach complete - no field_mapper.py needed!

---

## ✅ COMPLETED: Phase 4 (FederalRunner Execution Agent) - Steps 1-4

**Status:** ✅ Steps 1-4 COMPLETE, Step 5 NEXT

**Goal:** Execute wizards using Contract-First pattern and deploy to Google Cloud Run

**Reference:** `requirements/shared/CONTRACT_FIRST_FORM_AUTOMATION.md` Phase 2

### ✅ Completed - Steps 1-4

**✅ Step 1: Core infrastructure**
- ✅ Playwright execution client (`src/playwright_client.py`)
- ✅ Atomic execution pattern (launch → fill → extract → close)
- ✅ Field execution logic (fill, click, fill_enter, javascript_click, select)
- ✅ Screenshot capture after each page
- ✅ Configuration management (`src/config.py`, `src/logging_config.py`)
- ✅ Location: `mcp-servers/federalrunner-mcp/`

**✅ Step 2: Schema validator (NO field_mapper.py needed!)**
- ✅ Load User Data Schema from wizard-schemas/
- ✅ Validate user_data with jsonschema library (`src/schema_validator.py`)
- ✅ Map user_data to selectors via field_id
- ✅ Schema-first data collection - Claude reads schema naturally

**✅ Step 3: MCP tools (local testing)**
- ✅ `federalrunner_list_wizards()` - List available wizards
- ✅ `federalrunner_get_wizard_info(wizard_id)` - Return schema (THE CONTRACT)
- ✅ `federalrunner_execute_wizard(wizard_id, user_data)` - Validate + execute
- ✅ Location: `mcp-servers/federalrunner-mcp/src/execution_tools.py`

**✅ Step 4: Local pytest tests**
- ✅ All 3 MCP tools tested and passing
- ✅ Schema validation tests
- ✅ End-to-end execution tests with FSA wizard
- ✅ Runtime error test with visual validation loop
- ✅ Screenshot saving to `tests/test_output/screenshots/`
- ✅ Location: `mcp-servers/federalrunner-mcp/tests/test_execution_local.py`

**✅ Agent Instructions**
- ✅ Comprehensive instructions for Claude (619 lines)
- ✅ 6 mandatory phases (Discovery, Schema Analysis, Data Collection, Validation, Execution, Result Handling)
- ✅ Visual validation loop pattern from MDCalc
- ✅ Generic wizard selection (not hardcoded to FSA)
- ✅ Location: `agents/federalrunner-instructions.md`

### 🔄 NEXT: Step 5 - FastAPI MCP Server + Cloud Run Deployment

**Goal:** Deploy FederalRunner to Google Cloud Run with OAuth 2.1 authentication

**Reference Models:**
- ✅ MDCalc server.py: `requirements/reference/mdcalc/server.py`
- ✅ MDCalc auth.py: `requirements/reference/mdcalc/auth.py`
- ✅ MDCalc deployment: `requirements/reference/mdcalc/mdcalc-deploy-to-cloud-run.sh`
- ✅ Auth0 docs: `docs/auth0/AUTH0_CONCEPTS.md`, `docs/auth0/AUTH0_IMPLEMENTATION_GUIDE.md`
- ✅ MCP integration: `docs/mcp-integration/`

**Skip Claude Desktop testing** - Go directly to Cloud Run deployment for testing in Claude.ai/mobile

---

## ⬜ NOT STARTED: Phase 5 (Cloud Deployment)

**Status:** Will begin AFTER Phase 4 complete

### Overview

Deploy FederalRunner to Google Cloud Run with OAuth 2.1 authentication.

**Reference:**
- **`requirements/execution/EXECUTION_DEPLOYMENT_REQUIREMENTS.md`** ← Primary deployment spec
- `requirements/execution/EXECUTION_REQUIREMENTS.md` REQ-EXEC-011 through REQ-EXEC-015
- `requirements/shared/AUTHENTICATION_REQUIREMENTS.md`
- MDCalc reference: `requirements/reference/mdcalc/`

### Steps (High-Level)

**5.1 OAuth 2.1 Authentication**
- Auth0 API resource configuration
- JWT token validation (JWKS-based)
- Scope-based permissions (`federalrunner:read`, `federalrunner:execute`)
- Reference: `requirements/shared/AUTHENTICATION_REQUIREMENTS.md`

**5.2 Dockerfile** (REQ-DEPLOY-002)
- Multi-stage build
- Playwright + WebKit dependencies (NOT Chromium - FSA compatibility)
- Copy wizard files from shared location to `/app/wizards/`
- Verify wizard-structures/ and data-schemas/ directories present
- Set environment: `FEDERALRUNNER_WIZARDS_DIR=/app/wizards`, `BROWSER_TYPE=webkit`, `HEADLESS=true`
- Reference: `requirements/execution/EXECUTION_DEPLOYMENT_REQUIREMENTS.md` REQ-DEPLOY-002

**5.3 Deployment Script** (REQ-DEPLOY-003)
- Copy `../../wizards/` to build context before Docker build
- Deploy to Cloud Run with environment variables
- Clean up copied wizards after deployment
- Reference: `requirements/execution/EXECUTION_DEPLOYMENT_REQUIREMENTS.md` REQ-DEPLOY-003

**5.4 Cloud Run Configuration** (REQ-DEPLOY-005)
- 2 CPU, 2Gi memory, 60s timeout
- Environment variables for production
- Health check endpoint
- Reference: `requirements/execution/EXECUTION_DEPLOYMENT_REQUIREMENTS.md` REQ-DEPLOY-005

**5.5 Update Deployment Guide**
- Update `docs/deployment/DEPLOYMENT_GUIDE.md` with FederalRunner-specific steps
- Remove MDCalc-specific content
- Add FederalRunner deployment workflow
- Document dual-mode path configuration

**5.6 Claude.ai Integration**
- Remote MCP server configuration
- Production testing from Claude.ai web
- Mobile app testing (Android/iOS)

**5.7 Voice Demo (Samsung Galaxy Fold 7)**
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
- [ ] Create Dockerfile (REQ-DEPLOY-002)
- [ ] Create deployment script (REQ-DEPLOY-003)
- [ ] Configure Auth0 OAuth 2.1 (REQ-DEPLOY-006)
- [ ] Implement FastAPI server with OAuth
- [ ] Deploy to Cloud Run (REQ-DEPLOY-005)
- [ ] Update `docs/deployment/DEPLOYMENT_GUIDE.md` (remove MDCalc-specific content, add FederalRunner workflow)
- [ ] Test Cloud Run deployment (REQ-DEPLOY-007)
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
