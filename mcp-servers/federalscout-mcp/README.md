# FederalScout: AI-Powered Wizard Discovery via Claude Desktop

> **Interactive wizard structure discovery through visual exploration** — enabling Claude to map government form wizards through natural conversation

---

## 🌟 Overview

FederalScout is a local MCP (Model Context Protocol) server that enables Claude Desktop to discover and map complex multi-page form wizard structures through interactive visual exploration. It combines:

- **Playwright browser automation** - For precise interaction and navigation
- **Claude Vision** - For understanding page structure through screenshots
- **Self-correcting loops** - Visual validation of every action
- **Session persistence** - Browser state maintained across tool calls
- **JSON output** - Portable wizard structure files

**Result:** Complete wizard maps created through conversation, ready for automated execution by FederalRunner. Implements **Contract-First Form Automation** pattern - generates both Wizard Structure (Playwright instructions) and User Data Schema (THE CONTRACT).

---

## 🏗️ How It Works

### Discovery Flow

```
1. USER: "Discover the FSA wizard at https://studentaid.gov/aid-estimator/"

2. CLAUDE (via FederalScout tools):
   ├─ federalscout_start_discovery(url)
   │  └─ Launch browser, navigate, capture screenshot
   │
   ├─ [Analyzes screenshot with vision]
   │  └─ "I see a 'Start Estimate' button on the landing page"
   │
   ├─ federalscout_click_element("Start Estimate", type="text")
   │  └─ Click button, capture new screenshot
   │
   ├─ federalscout_get_page_info()
   │  └─ Extract all form elements (NO screenshot, to optimize size)
   │
   ├─ [Analyzes screenshot + element data]
   │  └─ "Page 1 has 6 fields: birthdate, marital status, state..."
   │
   ├─ federalscout_execute_actions([{action: fill, selector: #month, value: 05}, ...])
   │  └─ Execute all actions, capture ONE screenshot at end
   │
   ├─ federalscout_save_page_metadata({page_number: 1, fields: [...]})
   │  └─ Save to session + incremental JSON file
   │
   └─ REPEAT for Pages 2-6 until results page reached

3. CLAUDE: federalscout_complete_discovery(wizard_name="FSA Estimator", wizard_id="fsa-estimator")
   └─ Validate structure against Universal Schema, save wizard JSON, close browser

4. CLAUDE: federalscout_save_schema(wizard_id="fsa-estimator", schema_content={...})
   └─ Generate and save User Data Schema (THE CONTRACT)

5. OUTPUT:
   - wizards/structure-schemas/fsa-estimator.json (Wizard Structure - Playwright instructions)
   - wizards/data-schemas/fsa-estimator-schema.json (User Data Schema - THE CONTRACT)
```

### Key Features

✅ **Vision-Guided** - Claude sees screenshots, understands structure visually
✅ **Self-Correcting** - If action fails, Claude sees error and tries alternatives
✅ **Conversation-Optimized** - Batch operations, incremental saves, optimized screenshots
✅ **Session Management** - Browser state persists across multiple tool calls
✅ **Pattern Library** - Handles hidden elements, typeaheads, conditional fields
✅ **Data Safety** - Incremental saves prevent data loss on crashes

---

## 🛠️ MCP Tools (7 Clean, Focused Tools)

FederalScout exposes 7 tools through the MCP protocol (6 for discovery + 1 for schema generation):

### 1. `federalscout_start_discovery`

**Purpose:** Begin discovery session, navigate to wizard URL

**Parameters:**
- `url` (string, required): Starting URL of the wizard

**Returns:**
- `session_id` (string): Unique session identifier (save this!)
- `screenshot` (base64 image): Initial page screenshot
- `current_url` (string): Current browser URL
- `html_context` (object): Initial form elements found
- `message` (string): Summary of what was found

**Usage:**
```json
{
  "url": "https://studentaid.gov/aid-estimator/"
}
```

**When to use:** First action when starting wizard discovery

---

### 2. `federalscout_click_element`

**Purpose:** Click buttons, links, or any clickable element

**Parameters:**
- `session_id` (string, required): Session ID from start_discovery
- `selector` (string, required): Element selector (text, ID, or CSS)
- `selector_type` (string, optional): How to interpret selector
  - `"text"` - Match button/link text (e.g., "Start Estimate", "Continue")
  - `"id"` - Match element ID (e.g., "submit-button")
  - `"css"` - CSS selector (e.g., "button.primary", "#start-btn")
  - `"auto"` - Auto-detect (default)

**Returns:**
- `screenshot` (base64 image): Page after click
- `current_url` (string): New URL if navigation occurred
- `html_context` (object): Updated form elements
- `message` (string): Result description

**Usage:**
```json
{
  "session_id": "abc-123",
  "selector": "Start Estimate",
  "selector_type": "text"
}
```

**When to use:** Navigate between pages, click Continue buttons, activate start buttons

**Hidden element handling:** Automatically uses JavaScript click if standard click fails

---

### 3. `federalscout_execute_actions` **[⭐ PRIMARY TOOL - Universal Batch Actions]**

**Purpose:** Execute ANY combination of diverse actions in one call (drastically reduces tool calls and conversation size)

**Parameters:**
- `session_id` (string, required): Session ID from start_discovery
- `actions` (array, required): Array of action objects to execute in sequence

**Action object structure:**
```json
{
  "action": "fill",              // Required: Action type
  "selector": "#field_id",       // Required: Element selector
  "value": "some value",         // Optional: Value (required for fill/select actions)
  "selector_type": "auto"        // Optional: For click actions (auto/text/id/css)
}
```

**Supported action types:**
- `"fill"` - Standard text/number input
- `"fill_enter"` - Typeahead/autocomplete fields (fill + press Enter)
- `"click"` - Click visible buttons/links
- `"javascript_click"` - Click hidden radio buttons/checkboxes
- `"select"` - Select dropdown option

**Returns:**
- `screenshot` (base64 image): Page AFTER all actions complete (only ONE screenshot)
- `completed_count` (integer): Number of actions successfully completed
- `total_actions` (integer): Total actions attempted
- `failed_actions` (array): List of actions that failed with error details
- `message` (string): Summary of batch operation

**Usage:**
```json
{
  "session_id": "abc-123",
  "actions": [
    {"action": "fill", "selector": "#birth_month", "value": "05"},
    {"action": "fill", "selector": "#birth_day", "value": "15"},
    {"action": "fill", "selector": "#birth_year", "value": "2007"},
    {"action": "javascript_click", "selector": "#fsa_Radio_MaritalStatusUnmarried"},
    {"action": "fill_enter", "selector": "#fsa_Typeahead_StateOfResidence", "value": "Illinois"},
    {"action": "javascript_click", "selector": "#fsa_Radio_CollegeLevelFreshman"}
  ]
}
```

**When to use:**
- **PRIMARY TOOL** for all page interactions (fills, clicks, selections)
- Combines any actions: fill + click + fill_enter + javascript_click + select
- Reduces 6 individual tool calls (6 screenshots) → 1 batch call (1 screenshot)
- **Optimization:** 70-83% reduction in tool calls and conversation size

**Why it's best:**
- One tool call = one screenshot, regardless of action count or types
- Mix any combination of actions (not just fills)
- Simplifies agent decision-making (one tool for everything)

---

### 4. `federalscout_get_page_info`

**Purpose:** Extract detailed information about all form elements on current page

**Parameters:**
- `session_id` (string, required): Session ID

**Returns:**
- `current_url` (string): Current page URL
- `page_title` (string): Page title from document
- `elements` (object): Detailed element inventory
  - `inputs` (array): All input elements with id, name, type, visible status
  - `selects` (array): All select dropdowns with id, name, options (first 10)
  - `textareas` (array): All textarea elements
  - `buttons` (array): All buttons and submit inputs
- `summary` (object): Count of each element type
- `message` (string): Usage instructions

**IMPORTANT:** This tool does NOT return a screenshot (optimized to reduce conversation size). Reference the most recent screenshot from `start_discovery`, `click_element`, or `execute_actions`.

**Usage:**
```json
{
  "session_id": "abc-123"
}
```

**When to use:**
- After landing on a new page to understand its structure
- To get exact selectors for fields visible in screenshot
- To identify all interactive elements

**Filtering:** Automatically filters out non-form elements (chat widgets, feedback buttons, help widgets)

---

### 5. `federalscout_save_page_metadata`

**Purpose:** Save discovered page structure to session and incremental JSON file

**Parameters:**
- `session_id` (string, required): Session ID
- `page_metadata` (object, required): Complete page structure

**Page metadata structure:**
```json
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
```

**Returns:**
- `total_pages_discovered` (integer): Number of pages saved so far
- `partial_file` (string): Path to incremental save file
- `message` (string): Confirmation with page count

**Incremental Save:** Automatically writes `_partial_{session_id}.json` after each page to prevent data loss on crashes

**When to use:** After fully discovering and testing a page's fields

---

### 6. `federalscout_complete_discovery`

**Purpose:** Finalize discovery, validate against Universal Schema, save Wizard Structure JSON file

**Parameters:**
- `session_id` (string, required): Session ID
- `wizard_name` (string, required): Human-readable name (e.g., "FSA Student Aid Estimator")
- `wizard_id` (string, required): Filename slug (lowercase-hyphenated, e.g., "fsa-estimator")
- `start_action` (object, optional): Action required to start wizard

**Start action structure (if wizard has landing page):**
```json
{
  "description": "Click 'Start Estimate' button on landing page",
  "selector": "text=Start Estimate",
  "selector_type": "text"
}
```

**Returns:**
- `wizard_id` (string): Final wizard file name
- `saved_to` (string): Full path to saved JSON file
- `wizard_structure` (object): Complete wizard structure
- `validation` (object): Validation results
  - `is_complete` (boolean)
  - `has_required_fields` (boolean)
  - `warnings` (array): Any issues found

**Actions performed:**
1. Validates all saved pages
2. Validates against Universal Wizard Structure Schema (Contract-First pattern)
3. Creates final wizard JSON file
4. Removes temporary partial file
5. Closes browser session
6. Cleans up session from memory

**When to use:** After discovering all pages and reaching results page

**IMPORTANT:** After this succeeds, you MUST call `federalscout_save_schema` to generate the User Data Schema (Contract-First pattern).

---

### 7. `federalscout_save_schema`

**Purpose:** Save User Data Schema that defines THE CONTRACT for this wizard (Contract-First pattern)

**Parameters:**
- `wizard_id` (string, required): Wizard identifier (must match wizard just discovered)
- `schema_content` (object, required): Complete JSON Schema (draft-07) defining required user data

**Schema structure:**
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "FSA Student Aid Estimator - User Data",
  "description": "User data required to execute FSA student aid estimation",
  "type": "object",
  "required": ["birth_year", "marital_status", "state"],
  "properties": {
    "birth_year": {
      "type": "string",
      "description": "Student's birth year (4 digits)",
      "pattern": "^[0-9]{4}$"
    },
    "marital_status": {
      "type": "string",
      "description": "Student's marital status",
      "enum": ["married", "unmarried"]
    },
    "state": {
      "type": "string",
      "description": "State of legal residence (full name)"
    }
  }
}
```

**Returns:**
- `schema_path` (string): Path where schema was saved
- `wizard_id` (string): Wizard identifier
- `validation` (object): Schema validation results
  - `is_valid` (boolean)
  - `property_count` (integer)
  - `required_count` (integer)

**Actions performed:**
1. Validates schema is valid JSON Schema (draft-07)
2. Checks required fields ($schema, type, properties)
3. Creates `data-schemas/` directory if needed
4. Saves to `wizards/data-schemas/{wizard-id}-schema.json`

**When to use:** IMMEDIATELY after `federalscout_complete_discovery` succeeds

**CRITICAL:** Property names in schema MUST match `field_id` values from discovered wizard structure. This linkage enables automatic data mapping in FederalRunner.

---

## 🎯 Critical Patterns

FederalScout implements patterns learned from extensive FSA Estimator testing:

### Pattern 1: Hidden Radio Buttons

**Problem:** Government forms often hide radio buttons behind labels

**Solution:** Use `action="javascript_click"` in `federalscout_execute_actions`

```json
{
  "action": "javascript_click",
  "selector": "#fsa_Radio_MaritalStatusUnmarried"
}
```

**Why:** Standard Playwright click fails on hidden elements. JavaScript `click()` works regardless of visibility.

---

### Pattern 2: Typeahead/Autocomplete Fields

**Problem:** Fields that show suggestions as you type

**Solution:** Use `action="fill_enter"` in `federalscout_execute_actions`

```json
{
  "action": "fill_enter",
  "selector": "#fsa_Typeahead_StateOfResidence",
  "value": "Illinois"
}
```

**Why:** Typing the value shows suggestions, pressing Enter selects the first match.

---

### Pattern 3: Conditional Fields

**Problem:** Fields that only appear after certain selections

**Discovery approach:**
1. Fill prerequisite field (e.g., State)
2. Capture screenshot
3. Observe new field appeared (e.g., Grade Level)
4. Add new field to metadata
5. Fill new field

**Why:** You can't discover conditional fields until you trigger their appearance through interaction.

---

### Pattern 4: Universal Batch Actions

**Problem:** Individual tool calls create multiple screenshots and conversation bloat

**Solution:** Use `federalscout_execute_actions` to combine ANY actions (fill, click, select, etc.)

**Before:**
```
click_element(radio) → screenshot 1
fill_field(month) → screenshot 2
fill_field(day) → screenshot 3
fill_field(year) → screenshot 4
fill_field(state) → screenshot 5
click_element(grade) → screenshot 6
= 6 tool calls, 6 screenshots
```

**After:**
```
execute_actions([
  {action: javascript_click, selector: radio},
  {action: fill, selector: month, value: 05},
  {action: fill, selector: day, value: 15},
  {action: fill, selector: year, value: 2007},
  {action: fill_enter, selector: state, value: Illinois},
  {action: javascript_click, selector: grade}
])
  → ONE screenshot after ALL actions complete
= 1 tool call, 1 screenshot
```

**Impact:** 70-83% reduction in conversation size per page

---

### Pattern 5: Incremental Saves

**Problem:** Claude Desktop can crash mid-discovery, losing all progress

**Solution:** Automatic incremental saves after each page

**How it works:**
- `save_page_metadata` writes `_partial_{session_id}.json` after each page
- File contains all pages discovered so far
- On crash, partial file preserves progress
- On completion, partial file is removed

**Recovery:**
```bash
# Check for partial files
ls wizards/_partial_*.json

# Examine partial file
cat wizards/_partial_abc-123.json | jq '.pages | length'
# Shows: 3 (3 pages were saved before crash)

# Option 1: Copy partial to final file and edit
cp wizards/_partial_*.json wizards/fsa-estimator-recovered.json

# Option 2: Restart discovery (partial will be overwritten)
```

---

### Pattern 6: Conversation Size Optimization

**Problem:** Claude Desktop has conversation length limits (~100K characters)

**Optimizations implemented:**

1. **MCP ImageContent format** (50-70% reduction)
   - Images sent as separate ImageContent objects
   - NOT embedded as base64 strings in JSON text

2. **Universal batch actions** (70-83% reduction per page)
   - 6 individual actions → 1 batch action
   - 6 screenshots → 1 screenshot
   - Combines ANY action types (not just fills)

3. **Screenshot optimization** (55% size reduction)
   - Quality: 60 (down from 80)
   - Max size: 50KB (down from 100KB)
   - Viewport only (not full page)

4. **No screenshots from get_page_info**
   - Returns element data only
   - Reference previous screenshot from click/fill

5. **Element filtering**
   - Removes chat widgets, feedback buttons, help popups
   - Reduces element data size

**Combined result:** 89% reduction in conversation size per page

**Impact:**
- Before: Crashed at page 3 (8 screenshots/page)
- After: Completes 10-15+ pages (2 screenshots/page)

---

## 📊 Wizard Structure Output

FederalScout produces standardized JSON files ready for FederalRunner execution:

```json
{
  "wizard_id": "fsa-estimator",
  "name": "FSA Student Aid Estimator",
  "url": "https://studentaid.gov/aid-estimator/",
  "discovered_at": "2025-10-15T10:30:00.000Z",
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
        },
        {
          "label": "Marital Status - Unmarried",
          "field_id": "marital_status",
          "selector": "#fsa_Radio_MaritalStatusUnmarried",
          "field_type": "radio",
          "interaction": "javascript_click",
          "required": true,
          "options": ["married", "unmarried", "separated"],
          "example_value": "unmarried",
          "notes": "Hidden radio button, requires JavaScript click"
        },
        {
          "label": "State of Legal Residence",
          "field_id": "state",
          "selector": "#fsa_Typeahead_StateOfResidence",
          "field_type": "text",
          "interaction": "fill_enter",
          "required": true,
          "example_value": "Illinois",
          "notes": "Typeahead field, press Enter after typing"
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

**Key sections:**
- `wizard_id` - Unique identifier (filename without .json)
- `start_action` - How to enter the wizard (if not direct)
- `pages` - Array of page structures in order
- `fields` - Every field with selector, type, interaction, validation
- `continue_button` - How to navigate to next page

**Validation:** Each field includes example values tested during discovery

---

## 🚀 Quick Start

### Prerequisites
- **Python 3.11+** (MCP requires 3.10+)
- **Claude Desktop** installed

### Installation

```bash
# 1. Navigate to federalscout-mcp
cd mcp-servers/federalscout-mcp

# 2. Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Install Playwright browser (WebKit recommended)
playwright install webkit
```

### Configure Claude Desktop

Add FederalScout MCP server to Claude Desktop configuration at:
`~/Library/Application Support/Claude/claude_desktop_config.json`

**Quick example:**
```json
{
  "mcpServers": {
    "federalscout": {
      "command": "/absolute/path/to/federalscout-mcp/venv/bin/python",
      "args": ["/absolute/path/to/federalscout-mcp/src/server.py"],
      "env": {
        "FEDERALSCOUT_HEADLESS": "false",
        "FEDERALSCOUT_BROWSER_TYPE": "webkit",
        "FEDERALSCOUT_VIEWPORT_WIDTH": "1000",
        "FEDERALSCOUT_VIEWPORT_HEIGHT": "1000"
      }
    }
  }
}
```

**📖 Complete setup guide with all configuration options:**
- **Standard mode** (new browser each session)
- **Demo mode** (pre-positioned browser for screen recording)
- **Environment variables** explained
- **Troubleshooting** common issues

👉 **See [docs/discovery/CLAUDE_DESKTOP_SETUP.md](../../docs/discovery/CLAUDE_DESKTOP_SETUP.md) for detailed setup instructions**

### Restart Claude Desktop

1. Quit Claude Desktop completely (Cmd+Q on Mac)
2. Reopen Claude Desktop
3. Check Settings → Developer → MCP Servers
4. Verify "federalscout" shows as "Connected"

### Start Discovery

Open Claude Desktop and start a conversation:

```
YOU: Discover the FSA Student Aid Estimator wizard at
https://studentaid.gov/aid-estimator/
```

Claude will use FederalScout tools to:
1. Launch browser and navigate to URL
2. Analyze screenshot and click start button
3. Discover each page's fields systematically
4. Test fields with dummy data
5. Save page metadata after each page
6. Complete discovery and save JSON file

**Output:**
- `wizards/structure-schemas/fsa-estimator.json` (Wizard Structure)
- `wizards/data-schemas/fsa-estimator-schema.json` (User Data Schema - THE CONTRACT)

---

## 🧪 Testing

### Local Integration Tests

```bash
cd mcp-servers/federalscout-mcp
source venv/bin/activate

# Run all tests
pytest tests/ -v

# Run full FSA discovery test
pytest tests/test_discovery_local.py -v

# Run session persistence tests
pytest tests/test_session_persistence.py -v

# Visual debugging (browser visible)
FEDERALSCOUT_HEADLESS=false pytest tests/ -v -s
```

### Test Output

Tests create output in `tests/test_output/`:
- `logs/test_discovery.log` - Detailed test execution logs
- `wizards/` - Discovered wizard JSON files
- `screenshots/` - Browser screenshots captured during tests

**Watch logs in real-time:**
```bash
tail -f tests/test_output/logs/test_discovery.log
```

---

## 📁 Project Structure

```
federalscout-mcp/
├── src/                          # Source code
│   ├── server.py                 # MCP stdio server
│   ├── discovery_tools.py        # 7 MCP tool implementations
│   ├── playwright_client.py      # Browser automation client
│   ├── models.py                 # Pydantic data models
│   ├── config.py                 # Configuration management
│   └── logging_config.py         # Structured logging
│
├── tests/                        # Test suite
│   ├── conftest.py               # Pytest fixtures
│   ├── test_discovery_local.py   # Integration tests
│   └── test_session_persistence.py
│
├── scripts/                      # Utility scripts
│   └── setup.sh                  # Development environment setup
│
├── wizards/                      # Discovered wizard JSON files
├── logs/                         # Application logs
├── screenshots/                  # Browser screenshots
│
├── requirements.txt              # Python dependencies
└── README.md                     # This file
```

---

## ⚙️ Configuration

All configuration via environment variables (prefix with `FEDERALSCOUT_`):

### Browser Settings
- `FEDERALSCOUT_BROWSER_TYPE` - Browser engine: `webkit` (default), `chromium`, `firefox`
- `FEDERALSCOUT_HEADLESS` - Run headless: `true` | `false` (default: false)
- `FEDERALSCOUT_SLOW_MO` - Slow down actions in ms (default: 500)

### Session Settings
- `FEDERALSCOUT_SESSION_TIMEOUT` - Session timeout in seconds (default: 1800 = 30 min)

### Screenshot Settings
- `FEDERALSCOUT_SCREENSHOT_QUALITY` - JPEG quality 1-100 (default: 60)
- `FEDERALSCOUT_SCREENSHOT_MAX_SIZE_KB` - Target max size in KB (default: 50)
- `FEDERALSCOUT_SAVE_SCREENSHOTS` - Save to disk: `true` | `false` (default: true)

### Viewport Settings
- `FEDERALSCOUT_VIEWPORT_WIDTH` - Browser width in pixels (default: 1000)
- `FEDERALSCOUT_VIEWPORT_HEIGHT` - Browser height in pixels (default: 1000)

**For screen recording/demos:**
- **Width**: Adjust based on your recording layout
  - Split-screen (Claude + Browser): 1000-1200px
  - Full-screen browser: 1600-1920px
- **Height**: Use taller viewports to show more form fields
  - Standard: 1000-1400px
  - Tall (fit entire forms): 1600-1800px
- Intelligent zoom will automatically adjust content to fit the viewport

**Common configurations:**

```json
// Split-screen recording (Claude Desktop on left, browser on right)
"FEDERALSCOUT_VIEWPORT_WIDTH": "1000",
"FEDERALSCOUT_VIEWPORT_HEIGHT": "1000"

// Taller viewport to fit more fields
"FEDERALSCOUT_VIEWPORT_WIDTH": "1200",
"FEDERALSCOUT_VIEWPORT_HEIGHT": "1600"

// Full-screen browser demo
"FEDERALSCOUT_VIEWPORT_WIDTH": "1600",
"FEDERALSCOUT_VIEWPORT_HEIGHT": "1400"
```

### Demo Mode (for Screen Recording)

For clean screen recordings, you can use **demo mode** to pre-position the browser window:

- `FEDERALSCOUT_BROWSER_ENDPOINT` - Connect to existing browser: `http://localhost:9222`
- `FEDERALSCOUT_BROWSER_TYPE` - Must be `chromium` when using endpoint

**How to use demo mode:**

1. Add to `.env`:
   ```bash
   FEDERALSCOUT_BROWSER_ENDPOINT=http://localhost:9222
   FEDERALSCOUT_BROWSER_TYPE=chromium
   FEDERALSCOUT_VIEWPORT_WIDTH=1000
   FEDERALSCOUT_VIEWPORT_HEIGHT=1000
   ```

2. Launch demo browser:
   ```bash
   python scripts/start_browser_for_demo.py
   ```

3. Position browser window exactly where you want it (e.g., right side of screen)

4. Run your demo (pytest or Claude Desktop) - FederalScout will connect to the existing browser

**Benefits:**
- Browser window stays fixed (no movement or resizing)
- Perfect for screen recording split-screen layouts
- Predefined endpoint (no copy/paste needed)

See `scripts/README.md` for detailed demo mode documentation.

### Directory Settings
- `FEDERALSCOUT_WORKSPACE_ROOT` - Root directory (required for Claude Desktop)
- `FEDERALSCOUT_WIZARDS_DIR` - Where to save wizard JSON files (recommend: `discovery/wizards/`)
- `FEDERALSCOUT_LOG_DIR` - Where to save logs (recommend: `logs/`)
- `FEDERALSCOUT_SCREENSHOT_DIR` - Where to save screenshot files (recommend: `discovery/screenshots/`)

**Recommended structure:** Keep all discovery artifacts in a `discovery/` folder:
```
mcp-servers/federalscout-mcp/
├── discovery/
│   ├── wizards/       # Discovered wizard JSON files
│   └── screenshots/   # Browser screenshots
└── logs/              # Application logs
```

**Browser Compatibility:**
- **WebKit** (Safari) - Works in headless mode with FSA and most government sites ✅
- **Chromium** (Chrome) - Blocked by FSA in headless mode ❌
- **Firefox** - Blocked by FSA in headless mode ❌

**Recommendation:** Use WebKit for government sites with bot detection.

---

## 🔍 Troubleshooting

### Browser doesn't launch
```bash
# Reinstall Playwright browsers
playwright install webkit
```

### Session expired errors
- Sessions timeout after 30 minutes (configurable)
- Start a new discovery session

### Selector not found
1. Use `federalscout_get_page_info` to see all available elements
2. Check exact selector spelling and case
3. Try different selector_type (text → id → css)

### Tool calls fail in Claude Desktop
1. Check logs: `tail -f logs/federalscout.log`
2. Verify FederalScout shows as "Connected" in Settings
3. Restart Claude Desktop completely
4. Check MCP server command and args are absolute paths

### Screenshots too large
- Reduce `FEDERALSCOUT_SCREENSHOT_QUALITY` (try 50 or 40)
- Ensure `FEDERALSCOUT_SCREENSHOT_MAX_SIZE_KB` is set to 50
- Check screenshot sizes: `ls -lh screenshots/*.jpg`

### Conversation length errors
- Verify MCP server is using ImageContent format (check logs)
- Ensure agent is using `federalscout_execute_actions` for batch actions
- Reduce screenshot quality further if needed

**Detailed troubleshooting:** `/docs/discovery/TROUBLESHOOTING_INFO.md`

---

## 📚 Documentation

### For Users
- **[Claude Desktop Setup](../../docs/discovery/CLAUDE_DESKTOP_SETUP.md)** - Complete configuration guide
- **[Optimizations](../../docs/discovery/OPTIMIZATIONS.md)** - Conversation size management techniques
- **[Troubleshooting](../../docs/discovery/TROUBLESHOOTING_INFO.md)** - Common issues and solutions

### For Developers
- **[Agent Instructions](../../agents/federalscout-instructions.md)** - Discovery workflow patterns for Claude
- **[Discovery Requirements](../../requirements/discovery/DISCOVERY_REQUIREMENTS.md)** - Detailed specifications
- **[Playwright Patterns](../../requirements/discovery/PLAYWRIGHT_PATTERNS.md)** - Browser automation patterns
- **[MCP Tool Specifications](../../requirements/shared/MCP_TOOL_SPECIFICATIONS.md)** - Tool contracts

---

## 🎯 Best Practices

### For Effective Discovery

1. **Use universal batch actions** - Use `federalscout_execute_actions` for ALL page interactions (fills, clicks, selects)
2. **Watch for conditionals** - Fill fields sequentially, check screenshots for new fields appearing
3. **Test every field** - Use dummy data to verify selectors work
4. **Document interaction types** - Hidden elements need javascript_click, typeaheads need fill_enter
5. **Save incrementally** - Call save_page_metadata after each page
6. **Validate selectors** - Use get_page_info to confirm exact selectors

### For Reliability

1. **Let Claude see errors** - Screenshots show validation errors, allow self-correction
2. **Keep sessions active** - Complete discovery within 30-minute timeout
3. **Monitor conversation size** - Watch for length warnings, use batch operations
4. **Save partial progress** - Incremental saves protect against crashes
5. **Use WebKit** - Most compatible with government sites

---

## 📄 License

MIT License - See root [LICENSE](../../LICENSE) for details.

---

## 🤝 Contributing

Contributions welcome! See root [README.md](../../README.md) for contribution guidelines.

**Priority areas:**
- New wizard discoveries
- Browser compatibility improvements
- Error recovery enhancements
- Documentation and examples

---

**Built with ❤️ for accessible government services**

*Part of the FormFlow project - Making government forms conversationally accessible*
