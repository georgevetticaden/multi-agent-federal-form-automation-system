# Multi-Agent Federal Form Automation System - Implementation Guide for Claude Code

## Project Overview

Multi-Agent Federal Form Automation System enables automation of government form wizards through **Contract-First Form Automation** - a pattern where visual form discovery automatically generates type-safe contracts (JSON Schemas) that bridge human interaction and automated execution.

**Two specialized agents:**
1. **FederalScout** - Discovers wizard structures + generates schemas (local, Claude Desktop) ✅ **COMPLETE**
2. **FederalRunner** - Executes wizards with validated user data (local testing complete, cloud deployment in progress) 🚧 **PHASE 4 COMPLETE, PHASE 5 IN PROGRESS**

This guide directs Claude Code through systematic implementation from discovery to production deployment.

**📺 Watch the System:** [YouTube Technical Walkthrough](https://www.youtube.com/watch?v=IkKKLjBCnjY)

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

## ✅ COMPLETED: Phase 4 (FederalRunner Execution Agent) - All Steps Complete

**Status:** ✅ FULLY COMPLETE - Local execution engine ready for cloud deployment

**Goal:** Execute wizards using Contract-First pattern with atomic Playwright automation

**Reference:** `requirements/shared/CONTRACT_FIRST_FORM_AUTOMATION.md` Phase 2

### ✅ Completed - All Steps

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

**✅ Step 5: Additional Wizard Support & Demo Tests**
- ✅ Federal Loan Simulator "Borrow More" wizard discovery
- ✅ Repeatable field support (Add/Remove loan functionality)
- ✅ Array field handling in Playwright client
- ✅ Demo recording tests for both wizards (FSA + Loan Simulator)
- ✅ Non-headless Chromium tests with viewport optimization
- ✅ Test suite: 14+ tests covering all patterns

**✅ Agent Instructions**
- ✅ Comprehensive instructions for Claude (619 lines)
- ✅ 6 mandatory phases (Discovery, Schema Analysis, Data Collection, Validation, Execution, Result Handling)
- ✅ Visual validation loop pattern from MDCalc
- ✅ Generic wizard selection (not hardcoded to FSA)
- ✅ Location: `agents/federalrunner-instructions.md`

**✅ Execution Performance**
- ✅ FSA Student Aid Estimator: 8-15 seconds (7 pages, 17 fields)
- ✅ Loan Simulator: 10-20 seconds (6 pages, repeatable fields)
- ✅ 100% success rate in automated tests
- ✅ WebKit headless compatibility verified

---

## 🔄 IN PROGRESS: Phase 5 - FastAPI MCP Server + Cloud Run Deployment

**Goal:** Deploy FederalRunner to Google Cloud Run with OAuth 2.1 authentication

**Detailed Requirements Documentation:**
- 📘 **`requirements/execution/FASTAPI_MCP_SERVER_REQUIREMENTS.md`** ← FastAPI server implementation (REQ-SERVER-001 through REQ-SERVER-009)
- 📘 **`requirements/execution/AUTH0_CONFIGURATION_REQUIREMENTS.md`** ← Auth0 setup (REQ-AUTH0-001 through REQ-AUTH0-008)
- 📘 **`requirements/execution/EXECUTION_DEPLOYMENT_REQUIREMENTS.md`** ← Dockerfile + deployment (REQ-DEPLOY-001 through REQ-DEPLOY-007)

**Reference Models:**
- ✅ MDCalc server.py: `requirements/reference/mdcalc/server.py` (894 lines)
- ✅ MDCalc auth.py: `requirements/reference/mdcalc/auth.py` (306 lines)
- ✅ MDCalc deployment: `requirements/reference/mdcalc/mdcalc-deploy-to-cloud-run.sh` (337 lines)
- ✅ Auth0 concepts: `docs/auth0/AUTH0_CONCEPTS.md`
- ✅ MCP integration: `docs/mcp-integration/`

**Skip Claude Desktop testing** - Go directly to Cloud Run deployment for testing in Claude.ai/mobile

---

## 🔄 IN PROGRESS: Phase 5 (Cloud Deployment)

**Status:** Ready for implementation - detailed requirements complete

**Demo Script:** `docs/blog-demo/federalrunner_demo_realistic.txt`

### Overview

Deploy FederalRunner MCP server to Google Cloud Run with OAuth 2.1 authentication, following the proven MDCalc deployment pattern.

### Step 5.1: FastAPI MCP Server with OAuth 2.1

**📘 Detailed Requirements:** `requirements/execution/FASTAPI_MCP_SERVER_REQUIREMENTS.md`

**Implementation checklist:**
- [ ] Create `src/server.py` with FastAPI app (model after MDCalc server.py)
- [ ] Implement lifespan management (PlaywrightClient init/cleanup)
- [ ] Add CORS middleware (allow Claude.ai/mobile access)
- [ ] Add request logging middleware (debugging)
- [ ] Create health check endpoint (`GET /health`)
- [ ] Implement MCP protocol endpoints:
  - [ ] `HEAD /` - Protocol discovery
  - [ ] `GET /` - 405 Method Not Allowed (POST-only transport)
  - [ ] `POST /` - Main MCP handler (selective authentication)
  - [ ] `DELETE /` - Session termination
- [ ] Implement session management (create, validate, cleanup)
- [ ] Define 3 FederalRunner tools in `get_tools()`:
  - [ ] `federalrunner_list_wizards` (scope: federalrunner:read)
  - [ ] `federalrunner_get_wizard_info` (scope: federalrunner:read)
  - [ ] `federalrunner_execute_wizard` (scope: federalrunner:execute)
- [ ] Implement `execute_tool()` function with scope validation
- [ ] Copy `src/auth.py` from MDCalc (no changes needed)
- [ ] Add OAuth metadata endpoint (`GET /.well-known/oauth-protected-resource`)
- [ ] Update `src/config.py` with Auth0 environment variables
- [ ] Test locally without OAuth
- [ ] Test locally with M2M OAuth token

**Key patterns from MDCalc:**
- MCP Protocol 2025-06-18 (Streamable HTTP, POST-only)
- Selective authentication (initialize = no auth, tools = full auth)
- Session management for MCP protocol compliance
- Tool responses with text + image content blocks
- JSON-RPC error format

**Requirements:** REQ-SERVER-001 through REQ-SERVER-009 (9 requirements)

---

### Step 5.2: Auth0 Configuration

**📘 Detailed Requirements:** `requirements/execution/AUTH0_CONFIGURATION_REQUIREMENTS.md`

**Configuration checklist:**
- [ ] Create Auth0 API: "FederalRunner MCP Server"
  - [ ] Set Identifier (placeholder initially, update after deployment)
  - [ ] Set Signing Algorithm: RS256
- [ ] Define OAuth scopes:
  - [ ] `federalrunner:read` - List/get wizard info
  - [ ] `federalrunner:execute` - Execute wizards
- [ ] Enable Dynamic Client Registration (DCR):
  - [ ] Toggle ON in API settings
  - [ ] Policy: Open (public registration)
- [ ] Create M2M test application:
  - [ ] Name: "FederalRunner Test Client"
  - [ ] Authorize for FederalRunner API
  - [ ] Grant all scopes
  - [ ] Save Client ID and Secret
- [ ] Create test user:
  - [ ] Email/password for OAuth flow testing
  - [ ] Save credentials
- [ ] Save all credentials to `~/auth0-credentials-federalrunner.txt`
- [ ] Test M2M token request
- [ ] After deployment: Update API Identifier with real Cloud Run URL

**Important notes:**
- M2M apps require manual pre-authorization (Applications → APIs → Machine To Machine Applications)
- AUTH0_ISSUER must have trailing slash
- DCR allows Claude Android to self-register OAuth clients

**Requirements:** REQ-AUTH0-001 through REQ-AUTH0-008 (8 requirements)

---

### Step 5.3: Dockerfile

**📘 Detailed Requirements:** `requirements/execution/EXECUTION_DEPLOYMENT_REQUIREMENTS.md` REQ-DEPLOY-002

**Implementation checklist:**
- [ ] Create `Dockerfile` with multi-stage build
- [ ] Install Playwright system dependencies
- [ ] Install Playwright WebKit ONLY (FSA headless compatibility)
- [ ] Copy application code (`src/`)
- [ ] Copy wizard files (`wizards/`) to `/app/wizards/`
- [ ] Verify wizard directories exist (`wizard-structures/`, `data-schemas/`)
- [ ] Set environment variables:
  - [ ] `FEDERALRUNNER_WIZARDS_DIR=/app/wizards`
  - [ ] `FEDERALRUNNER_BROWSER_TYPE=webkit`
  - [ ] `FEDERALRUNNER_HEADLESS=true`
- [ ] Add health check
- [ ] Test build locally: `docker build -t federalrunner-mcp .`
- [ ] Test run locally: `docker run -p 8080:8080 federalrunner-mcp`

**Critical:** Use WebKit, NOT Chromium - FSA blocks headless Chromium

---

### Step 5.4: Deployment Script

**📘 Detailed Requirements:** `requirements/execution/EXECUTION_DEPLOYMENT_REQUIREMENTS.md` REQ-DEPLOY-003

**Implementation checklist:**
- [ ] Create `scripts/deploy-to-cloud-run.sh` (model after MDCalc)
- [ ] Create `.env.deployment.example` template
- [ ] Implement deployment steps:
  - [ ] Load configuration from `.env.deployment`
  - [ ] Validate configuration (required vars, CPU/memory ratios)
  - [ ] Set Google Cloud project
  - [ ] Verify billing enabled
  - [ ] Enable required APIs (run, cloudbuild)
  - [ ] Copy `../../wizards/` to build context
  - [ ] Verify wizard files exist
  - [ ] Deploy to Cloud Run (initial with placeholder URLs)
  - [ ] Get service URL
  - [ ] Update Cloud Run env vars with real URLs
  - [ ] Clean up build context
  - [ ] Test health endpoint
  - [ ] Test OAuth metadata endpoint
- [ ] Make executable: `chmod +x scripts/deploy-to-cloud-run.sh`
- [ ] Test deployment

**Resource configuration:**
- Memory: 2Gi (Playwright + WebKit)
- CPU: 2 (parallel execution)
- Timeout: 60s (FSA completes in 15-25s)
- Min instances: 0 (scale to zero)
- Max instances: 10 (concurrent requests)

---

### Step 5.5: Claude.ai Integration

**Goal:** Add FederalRunner as custom connector and test complete flow

**Steps:**
- [ ] Deploy to Cloud Run (get actual URL)
- [ ] Update Auth0 API Identifier with Cloud Run URL
- [ ] Update Cloud Run env vars (AUTH0_API_AUDIENCE, MCP_SERVER_URL)
- [ ] Add connector in Claude.ai:
  - [ ] Settings → Connectors → Add Connector
  - [ ] Name: FederalRunner
  - [ ] Description: Federal Form Automation
  - [ ] Server URL: Cloud Run URL
- [ ] Test OAuth flow:
  - [ ] Click "Connect"
  - [ ] Auth0 login page
  - [ ] Enter test user credentials
  - [ ] Consent screen
  - [ ] Click "Allow"
  - [ ] Verify "Connected" status
- [ ] Test in conversation:
  - [ ] "Calculate my federal student aid"
  - [ ] Verify `federalrunner_list_wizards()` called
  - [ ] Verify `federalrunner_get_wizard_info()` called
  - [ ] Provide complete user data
  - [ ] Verify `federalrunner_execute_wizard()` called
  - [ ] Verify results displayed with screenshots
- [ ] Test visual validation loop:
  - [ ] Provide invalid data (e.g., "Kerala, India" for state)
  - [ ] Verify error screenshot captured
  - [ ] Verify Claude analyzes screenshot and guides correction
- [ ] Test on Claude Mobile (Android/iOS)
- [ ] Verify OAuth sync to mobile (2 minutes)

**Reference:** `docs/mcp-integration/MCP_INTEGRATION_SUCCESS_STORY.md`

---

### Step 5.6: Voice Demo Recording

**Goal:** Record "Three Moments" technical demo for blog post

**📘 Demo Script:** `docs/blog-demo/federalrunner_demo_realistic.txt`

**Setup:**
- Device: Samsung Galaxy Fold 7
- App: Claude Mobile (Android)
- Screen recording: Native Android screen recorder
- Audio: Clear voice input

**Demo flow:**
- [ ] **Moment 1**: Natural voice query "Calculate my federal student aid"
- [ ] **Moment 2**: Provide all data in natural language (rich context upfront)
- [ ] **Moment 3**: Results displayed with interpretation
- [ ] Capture complete flow in <30 seconds
- [ ] Show hands-free operation
- [ ] Highlight visual validation loop (if error occurs)

**Post-production:**
- [ ] Record multiple takes
- [ ] Select best take
- [ ] Add captions (optional)
- [ ] Upload to blog assets

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

### ✅ Phase 3.5: Schema Generation (COMPLETE)
- ✅ Schema-first approach designed
- ✅ FederalScout generates User Data Schemas
- ✅ Wizard Data + User Data Schema artifacts

### ✅ Phase 4: FederalRunner Execution - ALL STEPS COMPLETE
- ✅ Core infrastructure (config, logging)
- ✅ Playwright execution client (atomic, WebKit)
- ✅ Schema validator (replaces field_mapper.py)
- ✅ MCP tools (schema-first approach)
- ✅ Local pytest tests (14+ tests, all patterns)
- ✅ Agent instructions (comprehensive, 619 lines)
- ✅ FSA Estimator support (7 pages, 17 fields, 8-15 seconds)
- ✅ Loan Simulator support (6 pages, repeatable fields, 10-20 seconds)
- ✅ Demo recording tests (non-headless, viewport optimization)
- ✅ 100% test success rate

### 🔄 Phase 5: Cloud Deployment (IN PROGRESS - Requirements Complete)
- 📘 **Detailed requirements created:**
  - ✅ FASTAPI_MCP_SERVER_REQUIREMENTS.md (9 requirements)
  - ✅ AUTH0_CONFIGURATION_REQUIREMENTS.md (8 requirements)
  - ✅ EXECUTION_DEPLOYMENT_REQUIREMENTS.md (7 requirements)
- ⬜ **Implementation pending:**
  - [ ] FastAPI MCP Server (REQ-SERVER-001 through REQ-SERVER-009)
  - [ ] Auth0 Configuration (REQ-AUTH0-001 through REQ-AUTH0-008)
  - [ ] Dockerfile (REQ-DEPLOY-002)
  - [ ] Deployment Script (REQ-DEPLOY-003)
  - [ ] Deploy to Cloud Run (REQ-DEPLOY-005)
  - [ ] Test Cloud Run deployment (REQ-DEPLOY-007)
  - [ ] Claude.ai integration and testing
  - [ ] Voice demo recording

---

## Success Criteria

### ✅ Discovery Phase (COMPLETE)
1. ✅ FederalScout discovers FSA wizard successfully
2. ✅ `fsa-student-aid-estimator.json` validates
3. ✅ All selectors tested via Claude Desktop

### ✅ Schema Generation Phase (COMPLETE)
4. ✅ Schema-first approach designed and validated
5. ✅ FederalScout generates User Data Schema for FSA
6. ✅ Both artifacts exist (wizard-data + wizard-schemas)
7. ✅ Schema is valid JSON Schema (draft-07)
8. ✅ Schema field_ids match wizard field_ids

### ✅ Execution Phase - Local (COMPLETE)
9. ✅ FederalRunner loads and returns schema to Claude
10. ✅ FederalRunner validates user_data before execution
11. ✅ field_id correctly maps to selectors
12. ✅ Pytest tests pass (14+ tests, all patterns covered)
13. ✅ Visual validation loop pattern validated
14. ✅ Agent instructions comprehensive and generic
15. ✅ FSA Estimator executes successfully (8-15 seconds)
16. ✅ Loan Simulator executes successfully (10-20 seconds with repeatable fields)
17. ✅ Demo recording tests work (viewport optimization, non-headless)
18. ✅ Universal design verified (2 different wizards, zero code changes)

### 🔄 Deployment Phase (IN PROGRESS - Requirements Ready)
19. 📘 Detailed requirements documentation complete (24 requirements)
20. ⬜ FastAPI MCP Server implemented with OAuth 2.1
21. ⬜ Auth0 configured with DCR enabled
22. ⬜ Cloud Run deployment successful
23. ⬜ OAuth authentication works (M2M + user flow)
24. ⬜ Claude.ai integration successful
25. ⬜ Claude Mobile integration successful
26. ⬜ Voice demo recorded
27. ⬜ Production-ready for additional wizards (SSA, IRS)

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

### From FederalRunner Implementation ✅
- **Atomic execution** - Launch → fill all pages → extract → close (8-15 seconds)
- **WebKit compatibility** - Headless mode works with FSA (Chromium doesn't)
- **Schema validation** - Contract-first validation before execution
- **Screenshot audit trail** - Full visual record of every page
- **Error recovery** - Visual validation loop with helpful messages
- **Repeatable fields** - Array handling for "Add a Loan" patterns
- **Universal design** - Same code works for FSA, Loan Simulator, future wizards

---

## Next Steps

**Focus: Phase 5 - Cloud Run Deployment with OAuth 2.1**

### Immediate Next Steps (in order):

1. **Implement FastAPI MCP Server** (`requirements/execution/FASTAPI_MCP_SERVER_REQUIREMENTS.md`)
   - Create `src/server.py` modeled after MDCalc
   - Copy `src/auth.py` from MDCalc (no changes needed)
   - Define 3 FederalRunner tools with proper scopes
   - Test locally with and without OAuth

2. **Configure Auth0** (`requirements/execution/AUTH0_CONFIGURATION_REQUIREMENTS.md`)
   - Create API: FederalRunner MCP Server
   - Define scopes: federalrunner:read, federalrunner:execute
   - Enable Dynamic Client Registration
   - Create M2M test application and test user
   - Test token requests

3. **Create Dockerfile** (`requirements/execution/EXECUTION_DEPLOYMENT_REQUIREMENTS.md`)
   - WebKit only (FSA compatibility)
   - Copy wizards to /app/wizards/
   - Test local Docker build and run

4. **Create Deployment Script**
   - Model after MDCalc deployment script
   - Copy wizards, deploy, update env vars, cleanup
   - Test deployment to Cloud Run

5. **Test in Claude.ai and Mobile**
   - Add custom connector
   - Test OAuth flow
   - Test all 3 tools end-to-end
   - Record voice demo on Samsung Galaxy Fold 7

### Ready to Begin Implementation

All requirements documentation is complete. Each step has:
- ✅ Detailed requirements (REQ-XXX-###)
- ✅ Implementation checklists
- ✅ Reference to working MDCalc examples
- ✅ Success criteria
- ✅ Troubleshooting guidance

---

## References

### Core Documentation
- **Contract-First Pattern:** `requirements/shared/CONTRACT_FIRST_FORM_AUTOMATION.md`
- **Wizard Structure Schema:** `requirements/shared/WIZARD_STRUCTURE_SCHEMA.md`
- **Execution Requirements:** `requirements/execution/EXECUTION_REQUIREMENTS.md`

### Phase 5 Deployment Requirements (NEW)
- **FastAPI MCP Server:** `requirements/execution/FASTAPI_MCP_SERVER_REQUIREMENTS.md` (9 requirements)
- **Auth0 Configuration:** `requirements/execution/AUTH0_CONFIGURATION_REQUIREMENTS.md` (8 requirements)
- **Deployment Infrastructure:** `requirements/execution/EXECUTION_DEPLOYMENT_REQUIREMENTS.md` (7 requirements)

### MDCalc Reference Implementation
- **Server:** `requirements/reference/mdcalc/server.py` (894 lines - proven pattern)
- **Auth:** `requirements/reference/mdcalc/auth.py` (306 lines - copy as-is)
- **Deployment:** `requirements/reference/mdcalc/mdcalc-deploy-to-cloud-run.sh` (337 lines - adapt for FederalRunner)

### Auth0 & MCP Integration
- **Auth0 Concepts:** `docs/auth0/AUTH0_CONCEPTS.md`
- **Auth0 Implementation:** `docs/auth0/AUTH0_IMPLEMENTATION_GUIDE.md`
- **MCP Success Story:** `docs/mcp-integration/MCP_INTEGRATION_SUCCESS_STORY.md`
- **MCP Troubleshooting:** `docs/mcp-integration/MCP_TROUBLESHOOTING_GUIDE.md`
- **MCP Handshake:** `docs/mcp-integration/MCP_HANDSHAKE_DIAGRAM.md`

### External Specs
- **JSON Schema Draft-07:** https://json-schema.org/draft-07/schema
- **MCP Protocol 2025-06-18:** https://modelcontextprotocol.io/specification/2025-06-18
- **OAuth 2.1:** https://oauth.net/2.1/
- **RFC 7591 (DCR):** https://datatracker.ietf.org/doc/html/rfc7591
- **RFC 9728 (OAuth Metadata):** https://datatracker.ietf.org/doc/html/rfc9728

### Demo & Testing
- **Blog Demo Script:** `docs/blog-demo/federalrunner_demo_realistic.txt`
- **Test Instructions:** `docs/execution/TEST_INSTRUCTIONS.md`
- **Agent Instructions:** `agents/federalrunner-instructions.md`
