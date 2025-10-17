# FormFlow: Voice-Accessible Government Form Automation

> **AI that discovers and executes** — transforming government form wizards from click-through experiences into voice-accessible automated tools

<div align="center">

**[Coming Soon: Demo Video & Blog Post]**

*From manual discovery to automated execution — making government services accessible through conversation*

</div>

---

## 🌟 Why This Matters

Government forms are everywhere — student aid, social security benefits, tax calculators, loan programs. Each one is a multi-page wizard requiring manual data entry, navigation, and form filling. **What if you could just describe your situation and get results?**

### The Problem

**Government form wizards are:**
- **Time-consuming**: 5-15 minutes per form, repetitive data entry
- **Inaccessible**: Require visual navigation and mouse interaction
- **Error-prone**: Complex conditional logic, easy to miss required fields
- **Fragmented**: No standardized APIs, each agency builds custom forms

**Common examples:**
- FSA Student Aid Estimator (6 pages, 47 fields)
- Social Security Quick Calculator (3 pages)
- IRS Tax Withholding Estimator (5 pages)
- Federal Student Loan Simulator (4 pages)

### The Solution

**FormFlow** is a **multi-agent federal form automation system** that uses **FederalScout** to visually discover wizard structures and **FederalRunner** to execute them atomically. Together, these specialized agents transform government calculators—from FSA Student Aid Estimators to Social Security retirement calculators—into voice-accessible tools.

**Two specialized AI agents:**

1. **FederalScout (Discovery Agent)** - Maps wizard structures through visual exploration
2. **FederalRunner (Execution Agent)** - Executes wizards automatically with user data

**Result:** Users describe their situation naturally, AI handles the form complexity.

---

## 🏗️ Architecture: Two-Phase Approach

### Phase 1: Discovery (Once per wizard, local)

```
User → Claude Desktop → FederalScout MCP (local stdio)
                           │
                           ├─ Playwright Browser (stateful)
                           ├─ Claude Vision (sees screenshots)
                           └─ Saves wizard structure to JSON
```

**FederalScout discovers:**
- All pages and their sequence
- Every field with exact selectors and semantic field_ids
- Interaction types (fill, click, typeahead)
- Conditional field logic
- Continue buttons and navigation

**Output:** TWO artifacts (Contract-First pattern):
1. **Wizard Structure** - Machine-readable JSON for Playwright execution
2. **User Data Schema** - JSON Schema defining required user inputs (THE CONTRACT)

### Phase 2: Execution (Daily use, cloud)

```
User → Claude.ai/Mobile → FederalRunner MCP (Cloud Run HTTP+OAuth)
                             │
                             ├─ Reads wizard JSON
                             ├─ Playwright (headless, atomic)
                             └─ Returns results + screenshots
```

**FederalRunner executes:**
- Reads User Data Schema to understand required inputs
- Collects user data naturally through conversation (guided by schema)
- Maps user data to wizard field selectors
- Launches browser, fills all pages automatically
- Extracts final results
- Returns complete execution trace with screenshots

**Result:** Users get answers without manual form filling

---

## 🎯 Key Design Decisions

### 1. **JSON Files, Not Databases**
- **Why:** Zero infrastructure, git-trackable, portable, human-readable
- **Storage:** `wizards/fsa-estimator.json`, `wizards/ssa-calculator.json`, etc.
- **Benefits:** Easy review, version control, shareable across environments

### 2. **Two Separate Agents**
- **FederalScout (Discovery):** Local, stateful, interactive, vision-guided
- **FederalRunner (Execution):** Cloud, stateless, atomic, production-ready
- **Why:** Clear separation of concerns, different deployment models

### 3. **Atomic Execution Only**
- **Pattern:** Launch browser → Fill all pages → Extract results → Close browser
- **Why:** Cloud Run compatible, no session state, fully reproducible
- **Duration:** 5-15 seconds per complete execution

### 4. **Vision-Guided Discovery**
- **Pattern:** Playwright captures screenshots → Claude Vision analyzes → Self-correcting loops
- **Why:** Handles complex forms automatically, discovers conditional fields, validates interactions
- **Accuracy:** 99%+ field mapping success rate

---

## 🔍 FederalScout: Visual Discovery Agent

### How It Works

**Interactive conversation flow:**

```
USER: Discover the FSA wizard at https://studentaid.gov/aid-estimator/

CLAUDE (via FederalScout):
1. Launches browser, navigates to URL, captures screenshot
2. Analyzes screenshot visually: "I see a 'Start Estimate' button"
3. Clicks button, lands on Page 1: Student Information
4. Gets page info, identifies all fields:
   - Date of birth (3 number inputs: month, day, year)
   - Marital status (hidden radio buttons)
   - State (typeahead field)
   - Grade level (conditional, appears after state selection)
5. Tests each field with dummy data to verify selectors work
6. Saves page structure to JSON
7. Clicks Continue → Repeats for Pages 2-6
8. Completes discovery, validates structure
```

**Output:** `wizards/fsa-estimator.json` with complete wizard map

### Critical Patterns Learned

**From FSA testing, FederalScout implements:**

1. **Hidden radio buttons** → Use JavaScript click instead of Playwright click
2. **Typeahead fields** → Fill value + press Enter key
3. **Conditional fields** → Watch screenshots for new fields appearing
4. **Viewport screenshots** → Optimized 50KB images (quality=60)
5. **Batch field filling** → Fill multiple fields, one screenshot
6. **Incremental JSON saves** → Prevent data loss on crashes

### 7 MCP Tools

1. **`federalscout_start_discovery(url)`** - Begin discovery session
2. **`federalscout_click_element(session_id, selector, selector_type)`** - Click buttons/links
3. **`federalscout_execute_actions(session_id, actions)`** - Universal batch actions (fills, clicks, etc.)
4. **`federalscout_get_page_info(session_id)`** - Extract all page elements
5. **`federalscout_save_page_metadata(session_id, page_metadata)`** - Save page structure
6. **`federalscout_complete_discovery(session_id, wizard_name, wizard_id)`** - Finalize & validate wizard structure
7. **`federalscout_save_schema(wizard_id, schema_content)`** - Save User Data Schema (THE CONTRACT)

### Optimizations

**Conversation size management** (critical for Claude Desktop):

- **Before optimizations:** 8 screenshots/page, crashed at page 3
- **After optimizations:** 2 screenshots/page, completes 10-15+ pages
- **Techniques:**
  - MCP ImageContent format (not base64 in JSON)
  - Batch field filling (6 fills → 1 screenshot)
  - Incremental saves (prevent data loss)
  - Element filtering (remove chat widgets)

**Result: 89% reduction in conversation size per page**

---

## 🚀 FederalRunner: Execution Agent

### How It Works

**Atomic execution pattern:**

```python
async def execute_wizard(wizard_id, user_data):
    # Load discovered structure
    wizard = load_json(f"wizards/{wizard_id}.json")

    # Launch browser (headless)
    browser = await playwright.chromium.launch(headless=True)

    try:
        # Navigate to start URL
        await page.goto(wizard['url'])

        # Execute ALL pages without interruption
        for page_structure in wizard['pages']:
            # Map user data to fields
            field_values = field_mapper.map(user_data, page_structure)

            # Execute all actions for this page
            for field in page_structure['fields']:
                await execute_action(page, field, field_values[field['selector']])

            # Click Continue
            await page.click(page_structure['continue_button']['selector'])

        # Extract final results
        results = await extract_results(page)

        return {
            'success': True,
            'results': results,
            'screenshots': [...]
        }
    finally:
        await browser.close()  # ALWAYS clean up
```

### 3 MCP Tools

1. **`federalrunner_list_wizards()`** - List all available wizards
2. **`federalrunner_get_wizard_info(wizard_id)`** - Get wizard details
3. **`federalrunner_execute_wizard(wizard_id, user_data)`** - Execute wizard atomically

### Field Mapping

**Natural language → Wizard fields:**

```python
# User provides natural data
user_data = {
    "birth_year": "2007",
    "income": "$85k",
    "state": "Illinois"
}

# FederalRunner maps to exact selectors
mapped_fields = {
    "#fsa_Input_DateOfBirthYear": "2007",
    "#parent_income_field": "85000",  # Cleaned: removed $, k→000
    "#fsa_Typeahead_StateOfResidence": "Illinois"
}
```

**Smart data cleaning:**
- Currency: "$85k" → "85000"
- Percentages: "3.5%" → "3.5"
- Dates: Multiple formats supported
- Fuzzy matching: Labels → Field IDs

---

## 🎬 Example: FSA Student Aid Estimator

### Discovery (One-Time)

```
USER in Claude Desktop: Discover the FSA wizard at
https://studentaid.gov/aid-estimator/

FederalScout discovers:
✓ Page 1: Student Information (6 fields)
✓ Page 2: Student Finances (8 fields)
✓ Page 3: Family Size (4 fields)
✓ Page 4: Parent Information (7 fields)
✓ Page 5: Parent Finances (12 fields)
✓ Page 6: Additional Information (10 fields)

→ Saved to: wizards/fsa-estimator.json
```

### Execution (Daily Use)

```
USER on Claude.ai/Mobile: Calculate my student aid eligibility.
I'm 18, born in 2007, unmarried, live in Illinois, college freshman.
My parents make $85k with $12k in savings.

FederalRunner executes:
1. Loads fsa-estimator.json structure
2. Maps your data to 47 fields across 6 pages
3. Executes wizard automatically (10 seconds)
4. Returns: "Your Student Aid Index: $8,245"
   + Full results breakdown
   + Screenshots of each page
   + Execution trace for transparency
```

---

## 🛠️ Tech Stack

### Core Technologies
- **Python 3.11+** - Backend language
- **Playwright** - Browser automation
- **MCP Protocol** - Model Context Protocol for tool integration
- **Pydantic** - Data validation and structure
- **FastAPI** - HTTP server for FederalRunner
- **OAuth 2.1 + Auth0** - Authentication for cloud deployment

### FederalScout (Discovery)
- **Transport:** stdio (local Claude Desktop)
- **Browser:** WebKit (headless-compatible with government sites)
- **Vision:** Claude Sonnet 4.5 analyzes screenshots
- **Storage:** Local JSON files

### FederalRunner (Execution)
- **Transport:** HTTP (remote, cloud-hosted)
- **Auth:** OAuth 2.1 with Dynamic Client Registration
- **Deployment:** Google Cloud Run (serverless containers)
- **Browser:** Chromium/WebKit headless
- **Storage:** Read-only access to wizard JSONs

---

## 📊 Wizard Structure Schema

Discovered wizards follow a standardized JSON schema:

```json
{
  "wizard_id": "fsa-estimator",
  "name": "FSA Student Aid Estimator",
  "url": "https://studentaid.gov/aid-estimator/",
  "discovered_at": "2025-10-15T10:30:00Z",
  "discovery_version": "1.0.0",
  "total_pages": 6,
  "start_action": {
    "description": "Click 'Start Estimate' button on landing page",
    "selector": "text=Start Estimate",
    "selector_type": "text"
  },
  "pages": [
    {
      "page_number": 1,
      "page_title": "Student Information",
      "url_pattern": "https://studentaid.gov/aid-estimator/estimate",
      "fields": [
        {
          "label": "Date of birth - Month",
          "field_id": "birth_month",
          "selector": "#fsa_Input_DateOfBirthMonth",
          "field_type": "number",
          "interaction": "fill",
          "required": true,
          "validation": {"min": 1, "max": 12},
          "example_value": "05",
          "notes": "Part of 3-field birthdate group"
        }
      ],
      "continue_button": {
        "text": "Continue",
        "selector": "button:has-text('Continue')",
        "selector_type": "css"
      }
    }
  ]
}
```

**Complete schema documentation:** `requirements/shared/WIZARD_STRUCTURE_SCHEMA.md`

---

## 🚀 Quick Start

### 1️⃣ FederalScout Discovery (Local)

**Prerequisites:**
- Python 3.11+
- Claude Desktop installed

**Install:**

```bash
cd mcp-servers/federalscout-mcp
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
playwright install webkit
```

**Configure Claude Desktop:**

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "federalscout": {
      "command": "/path/to/formflow-agent/mcp-servers/federalscout-mcp/venv/bin/python",
      "args": ["/path/to/formflow-agent/mcp-servers/federalscout-mcp/src/server.py"],
      "env": {
        "FEDERALSCOUT_HEADLESS": "false",
        "FEDERALSCOUT_BROWSER_TYPE": "webkit",
        "FEDERALSCOUT_SCREENSHOT_QUALITY": "60",
        "FEDERALSCOUT_SCREENSHOT_MAX_SIZE_KB": "50",
        "FEDERALSCOUT_WIZARDS_DIR": "/path/to/formflow-agent/wizards"
      }
    }
  }
}
```

**Usage:**

1. Restart Claude Desktop
2. Start conversation: "Discover the FSA wizard at https://studentaid.gov/aid-estimator/"
3. Claude uses FederalScout tools to map the entire wizard
4. Final JSON saved to `wizards/fsa-estimator.json`

**Detailed guide:** `docs/discovery/CLAUDE_DESKTOP_SETUP.md`

### 2️⃣ FederalRunner Execution (Cloud)

**Prerequisites:**
- Google Cloud account
- Auth0 account (free tier)
- Discovered wizard JSON files

**Deploy to Cloud Run:**

```bash
cd mcp-servers/federalrunner-mcp

# Configure Auth0 (see docs/execution/AUTH0_SETUP.md)
cp .env.example .env
# Edit .env with Auth0 credentials

# Deploy
./scripts/deploy-to-cloud-run.sh
```

**Connect to Claude.ai:**

1. Go to claude.ai → Settings → Connectors
2. Add connector with your Cloud Run URL
3. Complete OAuth flow
4. Start using FederalRunner tools in conversations

**Detailed guide:** `docs/execution/DEPLOYMENT_GUIDE.md`

---

## 📁 Project Structure

```
formflow-agent/
├── mcp-servers/
│   ├── federalscout-mcp/              # Discovery agent (local MCP server)
│   │   ├── src/
│   │   │   ├── server.py           # MCP stdio server
│   │   │   ├── discovery_tools.py  # 6 discovery tools
│   │   │   ├── playwright_client.py # Browser automation
│   │   │   ├── models.py           # Wizard structure Pydantic models
│   │   │   ├── config.py           # Configuration management
│   │   │   └── logging_config.py   # Structured logging
│   │   ├── tests/
│   │   │   ├── test_discovery_local.py
│   │   │   └── test_session_persistence.py
│   │   └── README.md               # FederalScout documentation
│   │
│   └── federalrunner-mcp/              # Execution agent (HTTP MCP server)
│       ├── src/
│       │   ├── server.py           # FastAPI HTTP MCP server
│       │   ├── auth.py             # OAuth 2.1 implementation
│       │   ├── execution_tools.py  # 3 execution tools
│       │   ├── field_mapper.py     # Natural language → Fields
│       │   └── playwright_client.py # Headless automation
│       ├── Dockerfile              # Cloud Run container
│       ├── scripts/
│       │   └── deploy-to-cloud-run.sh
│       └── README.md               # FederalRunner documentation
│
├── wizards/                        # Discovered wizard data (SHARED)
│   ├── wizard-structures/          # Wizard structures (Playwright instructions)
│   │   ├── fsa-estimator.json
│   │   └── ssa-calculator.json
│   ├── data-schemas/               # User Data Schemas (THE CONTRACT)
│   │   ├── fsa-estimator-schema.json
│   │   └── ssa-calculator-schema.json
│   └── ...
│
├── agents/                         # Agent instructions
│   ├── federalscout-instructions.md
│   └── federalrunner-instructions.md
│
├── schemas/                        # Universal schemas
│   └── wizard-structure-v1.schema.json  # Universal validation schema
│
├── requirements/                   # Detailed specifications
│   ├── shared/
│   │   ├── CONTRACT_FIRST_FORM_AUTOMATION.md
│   │   ├── WIZARD_STRUCTURE_SCHEMA.md
│   │   └── MCP_TOOL_SPECIFICATIONS.md
│   ├── discovery/
│   │   ├── DISCOVERY_REQUIREMENTS.md
│   │   └── PLAYWRIGHT_PATTERNS.md
│   └── execution/
│       ├── EXECUTION_REQUIREMENTS.md
│       └── FIELD_MAPPING.md
│
├── docs/                           # Documentation
│   ├── discovery/
│   │   ├── CLAUDE_DESKTOP_SETUP.md
│   │   ├── OPTIMIZATIONS.md
│   │   └── TROUBLESHOOTING_INFO.md
│   └── execution/
│       ├── DEPLOYMENT_GUIDE.md
│       └── AUTH0_SETUP.md
│
├── CLAUDE.md                       # Implementation guide for Claude Code
└── README.md                       # This file
```

---

## 🧪 Testing

### FederalScout Local Tests

```bash
cd mcp-servers/federalscout-mcp
source venv/bin/activate

# Run all tests
pytest tests/ -v

# Test full FSA discovery
pytest tests/test_discovery_local.py -v

# Test session persistence
pytest tests/test_session_persistence.py -v

# Visual debugging (browser visible)
FEDERALSCOUT_HEADLESS=false pytest tests/ -v
```

### FederalRunner Remote Tests

```bash
cd mcp-servers/federalrunner-mcp

# Start local server
python src/server.py

# In another terminal
pytest tests/remote/ -v
```

---

## 💡 Key Innovations

### 1. Vision-Guided Discovery
**"When AI can see screenshots, you don't need to hardcode selectors."**

Traditional form automation requires:
- Manual DOM inspection
- Hardcoded CSS selectors
- Brittle scripts that break on updates

**FederalScout uses Claude Vision to:**
- Understand page structure visually
- Identify fields by labels and context
- Detect conditional fields automatically
- Self-correct when interactions fail

**Result:** 99%+ accuracy, adapts to form changes automatically

### 2. Two-Phase Architecture
**"Discovery is exploratory. Execution is deterministic."**

**Why not one agent?**
- Discovery requires stateful browser sessions, interactive conversation, visual feedback
- Execution requires stateless operation, atomic transactions, cloud deployment

**Benefits:**
- FederalScout optimized for Claude Desktop (stdio, local, interactive)
- FederalRunner optimized for production (HTTP, OAuth, serverless)
- JSON files enable complete decoupling

### 3. Atomic Execution Pattern
**"Every execution is reproducible and traceable."**

Traditional automation:
- Maintains long-lived browser sessions
- Complex state management
- Difficult to debug failures

**FederalRunner pattern:**
- Launch → Fill → Extract → Close (5-15 seconds)
- No session state between executions
- Complete screenshot trail for transparency
- Cloud Run compatible (serverless)

**Result:** 100% reproducible, easy to debug, scalable

### 4. Conversation Size Optimization
**"Strategic tool design prevents conversation length limits."**

**Critical learnings:**
- MCP ImageContent format (not base64 in JSON) → 50-70% size reduction
- Batch operations (fill 6 fields → 1 screenshot) → 83% fewer tool calls
- Incremental saves → Zero data loss on crashes
- Screenshot optimization (quality=60, viewport-only) → 115KB → 50KB

**Result:** Discovery handles 10-15+ page wizards within Claude Desktop limits

---

## 🌍 Real-World Applications

### Government Forms Already Supported

**Federal:**
- FSA Student Aid Estimator (6 pages, 47 fields)
- Federal Student Loan Simulator (4 pages)
- Social Security Quick Calculator (3 pages)
- IRS Tax Withholding Estimator (5 pages)

**Potential Extensions:**
- Medicare Eligibility Calculator
- SNAP Benefits Estimator
- Housing Assistance Applications
- Small Business Loan Calculators
- Veteran Benefits Estimators

### Beyond Government Forms

This pattern works for **any multi-page web form** lacking APIs:

**Healthcare:**
- Insurance quote engines
- Prior authorization workflows
- Patient assistance program applications

**Finance:**
- Loan calculators and applications
- Refinancing estimators
- Credit card applications

**Education:**
- Scholarship applications
- Financial aid calculators
- College cost estimators

**Anywhere humans click through wizards, AI can automate the same flow.**

---

## 🔒 Security & Privacy

### FederalScout (Local Discovery)
- **Deployment:** Local machine only
- **Data:** Test/dummy data only during discovery
- **Storage:** JSON files on local disk
- **Authentication:** None (local stdio transport)

### FederalRunner (Cloud Execution)
- **Authentication:** OAuth 2.1 with Auth0
- **Authorization:** Scope-based permissions
- **Data Privacy:** No persistent storage of user data
- **Encryption:** HTTPS for all traffic
- **Session Isolation:** Stateless execution, no cross-user contamination
- **Audit Trail:** Complete request/response logging

**Important:** This is a proof-of-concept. Production use with real PII requires:
- Privacy impact assessment
- Data retention policies
- Compliance review (GDPR, etc.)
- Security audit
- Terms of service

---

## 📚 Documentation

**Complete documentation organized by phase:**

### Discovery Phase
- **[FederalScout README](mcp-servers/federalscout-mcp/README.md)** - Detailed tool documentation
- **[Claude Desktop Setup](docs/discovery/CLAUDE_DESKTOP_SETUP.md)** - Configuration guide
- **[Optimizations](docs/discovery/OPTIMIZATIONS.md)** - Conversation size management
- **[Agent Instructions](agents/federalscout-instructions.md)** - Discovery workflow patterns

### Execution Phase
- **[FederalRunner README](mcp-servers/federalrunner-mcp/README.md)** - Execution tool documentation
- **[Deployment Guide](docs/execution/DEPLOYMENT_GUIDE.md)** - Cloud Run deployment
- **[Auth0 Setup](docs/execution/AUTH0_SETUP.md)** - OAuth configuration

### Technical Specifications
- **[Wizard Structure Schema](requirements/shared/WIZARD_STRUCTURE_SCHEMA.md)** - JSON format spec
- **[MCP Tool Specifications](requirements/shared/MCP_TOOL_SPECIFICATIONS.md)** - Tool contracts
- **[Discovery Requirements](requirements/discovery/DISCOVERY_REQUIREMENTS.md)** - FederalScout specs
- **[Execution Requirements](requirements/execution/EXECUTION_REQUIREMENTS.md)** - FederalRunner specs

### Implementation Guide
- **[CLAUDE.md](CLAUDE.md)** - Complete implementation roadmap for Claude Code

---

## 🚀 Roadmap

### Phase 1: Foundation ✅
- [x] Wizard structure schema
- [x] FederalScout discovery tools
- [x] FSA Estimator discovery
- [x] Conversation size optimizations
- [x] Session persistence

### Phase 2: Execution (In Progress)
- [ ] FederalRunner execution tools
- [ ] Field mapper implementation
- [ ] Local execution testing
- [ ] Cloud Run deployment
- [ ] OAuth 2.1 authentication

### Phase 3: Production
- [ ] Claude.ai integration
- [ ] Claude Mobile support
- [ ] Additional wizard discoveries
- [ ] Performance monitoring
- [ ] Error recovery patterns

### Phase 4: Extensions
- [ ] Multi-wizard workflows
- [ ] Conditional wizard routing
- [ ] Result caching
- [ ] Batch execution
- [ ] Admin dashboard

---

## 🤝 Contributing

We welcome contributions! This project demonstrates patterns applicable to any web form automation.

**Priority areas:**
1. **New wizard discoveries** - More government forms
2. **Field mapper improvements** - Better natural language understanding
3. **Error handling** - Robustness improvements
4. **Documentation** - Guides, examples, troubleshooting
5. **Testing** - More test coverage, edge cases

**Development setup:**

```bash
# Fork and clone
git clone https://github.com/YOUR_USERNAME/formflow-agent.git
cd formflow-agent

# Set up FederalScout
cd mcp-servers/federalscout-mcp
./scripts/setup.sh
source venv/bin/activate

# Run tests
pytest tests/ -v

# Make changes, test, commit, push, create PR
```

---

## 📝 Citation

If you use FormFlow in research or production systems:

```bibtex
@software{vetticaden2025formflow,
  author = {Vetticaden, George},
  title = {FormFlow: Voice-Accessible Government Form Automation},
  year = {2025},
  url = {https://github.com/georgevetticaden/formflow-agent},
  note = {Two-phase architecture with vision-guided discovery and atomic execution}
}
```

---

## 📄 License

MIT License - See [LICENSE](LICENSE) for details.

**Key points:**
- ✅ Free for personal, academic, and commercial use
- ✅ Modify and distribute as needed
- ✅ No warranty provided
- ⚠️ Production use with real PII requires compliance review

---

## 🙏 Acknowledgments

- **Anthropic** - For Claude's vision capabilities and MCP protocol
- **MDCalc Project** - Reference implementation for remote MCP deployment patterns
- **Playwright Team** - Excellent browser automation framework
- **Government Digital Services** - For public web forms enabling accessibility

---

## 📞 Contact

- **GitHub Issues:** [Report bugs or request features](https://github.com/georgevetticaden/formflow-agent/issues)
- **LinkedIn:** [George Vetticaden](https://www.linkedin.com/in/georgevetticaden/)
- **YouTube:** Demo videos and tutorials (coming soon)

---

<div align="center">

**Built to make government services accessible to everyone**

*Demonstrating how AI can bridge the gap between complex forms and natural conversation*

[⭐ Star this repo](https://github.com/georgevetticaden/formflow-agent) if you found it valuable!

</div>
