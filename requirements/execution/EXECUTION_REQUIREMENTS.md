# FederalRunner Execution Agent Requirements

## Purpose

Define requirements for the FederalRunner Execution Agent, which executes discovered government wizard structures atomically using user-provided data, deployed on Google Cloud Run.

---

## Core Capabilities

### REQ-EXEC-001: Cloud Run Deployment
- **Requirement**: FederalRunner MUST run as HTTP-based MCP server on Google Cloud Run
- **Transport**: HTTP with Server-Sent Events (SSE) per MCP spec 2025-06-18
- **Authentication**: OAuth 2.1 with Auth0
- **Scalability**: Must handle concurrent executions
- **Rationale**: Stateless, scalable, accessible from Claude.ai and Claude Mobile

### REQ-EXEC-002: Atomic Execution Pattern
- **Requirement**: Each wizard execution MUST complete in single browser session
- **No Session State**: Cannot rely on state between tool calls (Cloud Run is stateless)
- **One Tool Call**: Primary execution happens in one MCP tool call
- **Rationale**: Cloud Run containers don't guarantee state persistence

### REQ-EXEC-003: JSON-Based Wizard Loading
- **Requirement**: Must read wizard structures from JSON files in `wizards/` directory
- **No Database**: No MongoDB or external database required
- **Packaging**: JSON files MUST be included in Docker container
- **Updates**: New wizards deployed via container rebuild

---

## Execution Tools

### REQ-EXEC-004: Tool Specifications

**Tool: `federalrunner_list_wizards`**
- OAuth Scope: `federalrunner:read`
- Input: None (or optional `category` filter)
- Actions:
  - Read all JSON files from `wizards/` directory
  - Parse basic metadata from each
  - Return list of available wizards
- Output:
```json
{
  "wizards": [
    {
      "wizard_id": "fsa-estimator.json",
      "name": "FSA Student Aid Estimator",
      "url": "https://studentaid.gov/aid-estimator/",
      "total_pages": 6,
      "discovered_at": "2025-01-15T..."
    }
  ],
  "count": 1
}
```

**Tool: `federalrunner_get_wizard_info`**
- OAuth Scope: `federalrunner:read`
- Input: `wizard_id` (filename, e.g., "fsa-estimator.json")
- Actions:
  - Load JSON file
  - Return complete structure for Claude to understand
- Output:
  - Full wizard structure JSON
  - Page summaries
  - Required input fields
- Purpose: Let Claude understand what data to collect from user

**Tool: `federalrunner_execute_wizard`** ⭐ (Primary Tool)
- OAuth Scope: `federalrunner:execute`
- Input:
  - `wizard_id`: Which wizard to execute
  - `user_data`: Object with user's information
  - `options`: Optional execution parameters
- Actions:
  - Load wizard structure from JSON
  - Launch Playwright browser (headless)
  - Navigate to wizard URL
  - For each page:
    - Map user data to fields using field_mapper
    - Fill all fields
    - Validate no errors
    - Click continue
  - Extract final results
  - Close browser
  - Return results + screenshots
- Output:
```json
{
  "success": true,
  "wizard_id": "fsa-estimator.json",
  "execution_time_ms": 8500,
  "results": {
    "student_aid_index": "19514",
    "eligibility": "Eligible for federal aid",
    "...": "extracted results"
  },
  "screenshots": [
    "base64_page1...",
    "base64_page2...",
    "base64_results..."
  ],
  "pages_completed": 6
}
```

**Tool: `federalrunner_validate_user_data`** (Optional helper)
- OAuth Scope: `federalrunner:read`
- Input:
  - `wizard_id`: Which wizard
  - `user_data`: Data to validate
- Actions:
  - Check if user data has all required fields
  - Validate data types
  - Suggest missing fields
- Output:
  - Validation status
  - Missing fields
  - Type mismatches
- Purpose: Help Claude collect complete data before execution

---

## Execution Workflow

### REQ-EXEC-005: User Interaction Flow

**Typical conversation:**
```
USER: "I need to calculate my Student Aid Index. 
       My family income is $85k, family of 4, $12k in savings."

CLAUDE: Let me help you calculate your SAI using the official 
        FSA Estimator.
        
        [Calls: federalrunner_get_wizard_info("fsa-estimator.json")]
        
        I see the FSA Estimator needs:
        - Student's birthdate
        - Student's marital status
        - Student's state
        - Student's grade level
        - Parent's marital status
        - Family size (you said 4 ✓)
        - Family income (you said $85k ✓)
        - Family savings (you said $12k ✓)
        
        I need a few more details:
        - Student's birth year?
        - Student's state of residence?
        - What grade will student be in Fall 2026?
        
USER: "Birth year 2007, Illinois, will be freshman"

CLAUDE: Perfect! Executing the FSA Estimator...

        [Calls: federalrunner_execute_wizard(
            wizard_id="fsa-estimator.json",
            user_data={
                "birth_year": "2007",
                "birth_month": "01",
                "birth_day": "01",
                "marital_status": "unmarried",
                "state": "Illinois",
                "grade_level": "freshman",
                "parent_married": "yes",
                "family_size": "4",
                "parent_income": "85000",
                "student_income": "0",
                "parent_assets": "12000",
                "student_assets": "0"
            }
        )]
        
        Your Student Aid Index (SAI) is: $19,514
        
        This means your family is expected to contribute $19,514 
        toward college costs. You are eligible for federal aid.
```

### REQ-EXEC-006: Data Mapping Strategy

**Field Mapper responsibilities:**
1. Map user's natural language data to wizard fields
2. Handle different user input formats
3. Provide sensible defaults where needed
4. Validate data types match field requirements

**Example mapping:**
```python
# User says: "income $85k"
# Mapper converts to:
{
    "parent_income_field": "85000"  # Remove $, k → 000
}

# User says: "unmarried student"
# Mapper converts to:
{
    "marital_status_field": "unmarried",  # Match wizard's option
    "marital_status_selector_value": "#fsa_Radio_MaritalStatusUnmarried"
}

# User says: "Illinois"
# Mapper converts to:
{
    "state_field": "Illinois"  # Exact match for typeahead
}
```

### REQ-EXEC-007: Error Handling During Execution

**Validation Errors:**
- If form shows validation errors after filling:
  - Take screenshot
  - Extract error messages
  - Return structured error to Claude
  - Claude asks user for corrected data

**Browser Errors:**
- If page doesn't load:
  - Retry up to 2 times with exponential backoff
  - If still fails, return error with screenshot
  
**Selector Failures:**
- If selector not found:
  - Try alternative selectors from JSON structure
  - If all fail, return error
  - Suggest wizard needs re-discovery

**Timeout Errors:**
- Maximum execution time: 60 seconds
- If exceeded, kill browser and return timeout error

---

## Technical Requirements

### REQ-EXEC-008: Playwright Configuration

**Browser launch:**
```python
browser = await playwright.chromium.launch(
    headless=True,
    args=[
        '--disable-gpu',
        '--no-sandbox',
        '--disable-dev-shm-usage'  # Important for Cloud Run
    ]
)
```

**Page configuration:**
```python
page = await browser.new_page(
    viewport={'width': 1280, 'height': 720},
    user_agent='Mozilla/5.0...'  # Standard user agent
)
```

**Timeouts:**
- Page load: 30 seconds
- Element wait: 10 seconds
- Navigation: 15 seconds

### REQ-EXEC-009: Screenshot Management

**During execution:**
- Take screenshot after completing each page
- Take screenshot of final results page
- Optimize: JPEG, 80% quality, max 100KB each
- Return all screenshots in execution response

**Purpose:**
- Visual confirmation for user
- Debugging failed executions
- Transparency (user sees what happened)

### REQ-EXEC-010: Result Extraction

**Requirements:**
- Must extract key results from final page
- Use visual landmarks (bold text, headings, tables)
- Return structured data, not just screenshot
- Handle different result formats per wizard

**FSA Example:**
```python
results = {
    "student_aid_index": extract_sai(page),
    "federal_pell_grant_estimate": extract_pell(page),
    "eligibility_status": extract_eligibility(page),
    "cost_of_attendance": extract_coa(page)
}
```

---

## Authentication Requirements

### REQ-EXEC-011: OAuth 2.1 Implementation

**OAuth Provider:** Auth0
**Grant Type:** Client Credentials
**Scopes:**
- `federalrunner:read` - List wizards, get info
- `federalrunner:execute` - Execute wizards

**Token Validation:**
- Validate on every tool call
- Check token expiration
- Verify required scopes
- Handle token refresh (if using refresh tokens)

**Reference:** MDCalc auth.py implementation patterns

### REQ-EXEC-012: MCP Authentication Flow

Per MCP spec 2025-06-18:
1. Client requests tools/list (may require auth)
2. Client requests tools/call (requires auth)
3. Server validates OAuth token
4. Server executes tool
5. Server returns results

**Security:**
- Never log user data
- Never log OAuth tokens
- Use HTTPS only
- Validate all inputs

---

## Deployment Requirements

### REQ-EXEC-013: Docker Container

**Dockerfile requirements:**
- Base: Python 3.11+
- Install Playwright + Chromium
- Copy wizard JSON files to container
- Install Python dependencies
- Expose port 8080
- Health check endpoint

**Container size optimization:**
- Remove Playwright browsers not needed (keep only Chromium)
- Use multi-stage build
- Minimize layers

### REQ-EXEC-014: Cloud Run Configuration

**Service settings:**
```yaml
CPU: 2
Memory: 2Gi
Min instances: 0
Max instances: 10
Timeout: 60s
Port: 8080
```

**Environment variables:**
```bash
AUTH0_DOMAIN=your-domain.us.auth0.com
AUTH0_ISSUER=https://your-domain.us.auth0.com/
AUTH0_API_AUDIENCE=https://your-api-identifier
PORT=8080
ENVIRONMENT=production
LOG_LEVEL=INFO
```

**Deploy command:**
```bash
gcloud run deploy federalrunner-mcp \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars="..." \
  --timeout=60s \
  --memory=2Gi \
  --cpu=2
```

### REQ-EXEC-015: Monitoring & Logging

**Structured logging:**
- Request IDs for tracing
- Execution time metrics
- Success/failure rates
- Error types and frequencies

**Cloud Run logging:**
- Log to stdout (Cloud Run captures)
- Include severity levels
- Structured JSON for Cloud Logging

**Monitoring:**
- Track execution times
- Monitor error rates
- Alert on deployment failures
- Track OAuth errors

---

## Testing Requirements

### REQ-EXEC-016: Local Testing

**Unit tests:**
- Test field mapper logic
- Test result extraction
- Mock Playwright for fast tests

**Integration tests:**
- Test complete execution with real browser (local)
- Test with fsa-estimator.json
- Verify results extraction
- Test error handling

### REQ-EXEC-017: Remote Testing

**Prerequisites:**
- FederalRunner deployed to Cloud Run
- Auth0 configured with test client
- Test OAuth tokens available

**Test suite:**
```bash
# Test OAuth flow
python tests/remote/test_auth_flow.py

# Test MCP protocol
python tests/remote/test_mcp_protocol.py

# Test FSA execution
python tests/remote/test_fsa_execution.py

# Test error handling
python tests/remote/test_error_scenarios.py
```

---

## Success Criteria

FederalRunner Execution Agent is successful when:
1. ✅ Deployed successfully on Cloud Run
2. ✅ OAuth authentication works with Auth0
3. ✅ Can execute fsa-estimator.json successfully
4. ✅ Extracts accurate results from FSA
5. ✅ Returns helpful screenshots
6. ✅ Handles errors gracefully
7. ✅ Execution completes in <10 seconds
8. ✅ Works from Claude.ai on desktop
9. ✅ Works from Claude.ai on mobile
10. ✅ Accessible via voice on mobile

---

## References

- Wizard Structure Schema: `requirements/shared/WIZARD_STRUCTURE_SCHEMA.md`
- Field Mapping: `requirements/execution/FIELD_MAPPING.md`
- Error Handling: `requirements/execution/ERROR_HANDLING.md`
- Auth0 Setup: MDCalc `docs/auth0/` (reference)
- Deployment Guide: MDCalc `docs/deployment/` (reference)
- MCP Integration: MDCalc `docs/mcp-integration/` (reference)