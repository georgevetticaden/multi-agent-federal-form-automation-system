# FederalScout Discovery Agent Requirements

## Purpose

Define requirements for the FederalScout Discovery Agent, which enables interactive wizard structure discovery through Claude Desktop using Playwright automation and Claude Vision.

---

## Core Capabilities

### REQ-DISC-001: Local MCP Server
- **Requirement**: FederalScout MUST run as a local MCP server using stdio transport
- **Runtime**: Python-based MCP server compatible with Claude Desktop
- **Configuration**: Must be configurable via Claude Desktop's MCP settings
- **Rationale**: Enables stateful browser sessions during discovery conversation

### REQ-DISC-002: Playwright Integration
- **Requirement**: Must use Playwright for browser automation
- **Browser**: Chromium-based automation
- **Mode**: Both headless and non-headless modes for debugging
- **State Management**: Browser instances MUST persist across tool calls within same session

### REQ-DISC-003: Claude Vision Integration
- **Requirement**: All tool responses with screenshots MUST return base64-encoded images
- **Format**: JPEG format, optimized for size (target: <100KB per screenshot)
- **Purpose**: Enable Claude to visually understand page structure
- **Content**: Screenshots MUST capture full page, including below-fold content

---

## Discovery Tools

### REQ-DISC-004: Session Management Tools

**Tool: `federalscout_start_discovery`**
- Input: `url` (string) - Starting URL of the wizard
- Actions:
  - Launch Playwright browser instance
  - Navigate to provided URL
  - Wait for page load
  - Take full-page screenshot
  - Extract basic HTML context (buttons, links, inputs)
  - Generate unique session_id
  - Store session in memory
- Output:
  - `session_id`: Unique identifier for this discovery session
  - `screenshot`: Base64-encoded JPEG
  - `current_url`: Actual URL after navigation
  - `html_context`: Array of visible interactive elements (first 30)
  - `message`: Description of what Claude should do next

**Tool: `federalscout_click_element`**
- Input:
  - `session_id`: Reference to active session
  - `selector`: CSS selector or text to click
  - `selector_type`: 'text' | 'id' | 'css' | 'auto'
- Actions:
  - Retrieve browser from session
  - Attempt to click element using specified strategy
  - Wait for navigation/changes
  - Take screenshot of result
  - Extract HTML context of new page
- Output:
  - `success`: Boolean
  - `screenshot`: Base64-encoded JPEG
  - `current_url`: URL after click
  - `html_context`: Elements on new page
  - `error`: Error message if failed


**Tool: `federalscout_get_page_info`**
- Input: `session_id`
- Actions:
  - Take current screenshot
  - Extract detailed element information:
    - All `<input>` elements with type, id, name, class, visible status
    - All `<select>` elements with options
    - All `<textarea>` elements
    - All buttons
  - Get current URL
- Output:
  - `screenshot`: Base64-encoded JPEG
  - `current_url`: Current page URL
  - `elements`: Structured element information
  - `page_title`: Page title if available

**Tool: `federalscout_save_page_metadata`**
- Input:
  - `session_id`: Reference to active session
  - `page_metadata`: JSON object with page structure
- Actions:
  - Validate page metadata structure
  - Append to session's discovered pages
  - Store in memory
- Output:
  - `success`: Boolean
  - `total_pages_discovered`: Count of pages found so far
  - `message`: Confirmation

**Tool: `federalscout_complete_discovery`**
- Input:
  - `session_id`: Reference to active session
  - `wizard_name`: Display name for the wizard
  - `wizard_id`: Slug for filename (e.g., "fsa-estimator")
- Actions:
  - Compile complete wizard structure from session
  - Validate structure against schema
  - Save to `wizards/{wizard_id}.json`
  - Close browser
  - Clean up session
- Output:
  - `success`: Boolean
  - `wizard_id`: Filename of saved structure
  - `saved_to`: Full path to JSON file
  - `wizard_structure`: Complete structure for review

---

## Discovery Workflow Requirements

### REQ-DISC-005: Interactive Discovery Process

**Phase 1: Initial Navigation**
1. User provides starting URL
2. FederalScout launches browser and navigates
3. Claude sees screenshot via Vision
4. Claude identifies "Start" button or initial action
5. Claude calls `federalscout_click_element` to begin wizard

**Phase 2: Page-by-Page Discovery**
For each wizard page:
1. Claude sees screenshot of current page
2. Claude calls `federalscout_get_page_info` for detailed element data
3. Claude analyzes visual layout + HTML context
4. Claude identifies:
   - All input fields and their labels
   - Correct selectors for each field
   - Field types and interaction methods
   - Continue/Next button
5. Claude tests filling each field with dummy data
6. If field fails, Claude tries alternative selectors
7. Once page is understood, Claude calls `federalscout_save_page_metadata`
8. Claude clicks Continue to next page
9. Repeat until final page reached

**Phase 3: Completion**
1. All pages discovered and validated
2. Claude calls `federalscout_complete_discovery`
3. Structure saved to JSON file
4. Browser closed, session cleaned

### REQ-DISC-006: Self-Correction During Discovery

**When selector fails:**
1. Tool returns `success: false` with error message
2. Claude sees screenshot of current state
3. Claude analyzes why it failed (vision)
4. Claude tries alternative selector approach
5. Maximum 3 retries per field before asking user for help

**Common correction patterns to handle:**
- Hidden radio buttons → use `javascript_click` instead of `click`
- Dynamic content → add wait times
- Typeahead fields → use `fill_enter` instead of `fill`
- Duplicate text selectors → use unique IDs instead

### REQ-DISC-007: Validation Requirements

**Before saving page metadata:**
- ✅ All visible fields must be identified
- ✅ Each field must have tested selector
- ✅ Continue button must be found
- ✅ Page must be navigable to next page with test data

**Before completing discovery:**
- ✅ At least one page discovered
- ✅ All pages have continue buttons (except last)
- ✅ Test execution reaches final page
- ✅ Structure matches schema requirements

---

## Technical Requirements

### REQ-DISC-008: Session State Management

**In-memory session storage:**
```python
active_sessions = {
    "session-id-123": {
        'playwright': <playwright_instance>,
        'browser': <browser_object>,
        'page': <page_object>,
        'url': "https://...",
        'pages_discovered': [],
        'started_at': timestamp,
        'last_activity': timestamp
    }
}
```

**Session lifecycle:**
- Created: `federalscout_start_discovery`
- Used: All other tools reference session_id
- Cleaned: `federalscout_complete_discovery` or timeout (30 min)

### REQ-DISC-009: Screenshot Optimization

- Format: JPEG with 80% quality
- Max size: 100KB per screenshot
- Viewport: 1280x720 for consistency
- Full page: Must capture content below fold
- Encoding: Base64 for MCP transport

### REQ-DISC-010: HTML Context Extraction

For each page, extract:
```python
{
    'inputs': [
        {
            'type': 'text|number|radio|checkbox',
            'id': 'element_id',
            'name': 'element_name',
            'class': 'class_names',
            'visible': True|False,
            'value': 'current_value'
        }
    ],
    'selects': [...],
    'textareas': [...],
    'buttons': [...]
}
```

**Limits:**
- First 50 elements of each type
- Exclude hidden elements unless they have IDs
- Include visibility status

### REQ-DISC-011: Error Handling

**Tool-level errors:**
- All tools MUST return structured errors
- Include error type, message, and screenshot
- Never throw exceptions that crash server
- Log all errors for debugging

**Browser crashes:**
- Detect browser disconnection
- Clean up session gracefully
- Return clear error to Claude
- Allow restart with new session

---

## Configuration Requirements

### REQ-DISC-012: Environment Configuration

Required environment variables:
```bash
# Optional - defaults provided
FEDERALSCOUT_HEADLESS=false          # Show browser for debugging
FEDERALSCOUT_SLOW_MO=500             # Slow down actions (ms)
FEDERALSCOUT_SESSION_TIMEOUT=1800    # 30 minutes
FEDERALSCOUT_SCREENSHOT_QUALITY=80   # JPEG quality (1-100)
```

### REQ-DISC-013: Claude Desktop Integration

MCP configuration for Claude Desktop:
```json
{
  "mcpServers": {
    "federalscout": {
      "command": "python",
      "args": ["-m", "federalscout_mcp.server"],
      "cwd": "/path/to/formflow-agent/mcp-servers/federalscout-mcp",
      "env": {
        "FEDERALSCOUT_HEADLESS": "false"
      }
    }
  }
}
```

---

## Testing Requirements

### REQ-DISC-014: Local Testing

**Unit tests:**
- Test each tool independently
- Mock Playwright for fast tests
- Verify JSON structure generation

**Integration tests:**
- Test complete discovery flow with FSA
- Verify browser session persistence
- Test self-correction on selector failures
- Verify final JSON file creation

**Manual testing:**
- Test discovery with Claude Desktop
- Verify visual feedback is helpful
- Test with multiple wizard types

---

## Success Criteria

FederalScout Discovery Agent is successful when:
1. ✅ Can discover FSA Estimator wizard completely
2. ✅ Saves valid `fsa-estimator.json` structure file
3. ✅ Self-corrects on selector failures
4. ✅ Provides clear visual feedback via screenshots
5. ✅ Completes discovery in <20 tool calls
6. ✅ Discovered structure enables successful execution
7. ✅ Works reliably with Claude Desktop
8. ✅ Browser state persists across tool calls
9. ✅ Session cleanup works properly
10. ✅ Error messages are actionable

---

## References

- Wizard Structure Schema: `requirements/shared/WIZARD_STRUCTURE_SCHEMA.md`
- FSA Test Results: `requirements/reference/fsa-test-results/`
- Playwright Patterns: `requirements/discovery/PLAYWRIGHT_PATTERNS.md`
- Visual Validation: `requirements/discovery/VISUAL_VALIDATION.md`