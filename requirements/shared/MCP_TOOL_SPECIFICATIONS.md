# MCP Tool Specifications

## Purpose

Define the complete MCP tool interface specifications for both FederalScout (discovery) and FederalRunner (execution) agents.

---

## MCP Protocol Version

**Target:** MCP Specification 2025-06-18
**Transport:**
- FederalScout: stdio (local)
- FederalRunner: HTTP with SSE (cloud)

---

## FederalScout Discovery Tools

### Tool: `federalscout_start_discovery`

**Purpose:** Begin wizard structure discovery session

**OAuth Scope:** None (local only)

**Parameters:**
```json
{
  "url": {
    "type": "string",
    "description": "Starting URL of the government wizard",
    "required": true,
    "example": "https://studentaid.gov/aid-estimator/"
  }
}
```

**Response:**
```json
{
  "session_id": "string (UUID)",
  "screenshot": "string (base64 JPEG)",
  "current_url": "string",
  "html_context": [
    {
      "tag": "button|a|input|select",
      "type": "string|null",
      "id": "string|null",
      "class": "string|null",
      "text": "string|null"
    }
  ],
  "message": "string (next steps guidance)"
}
```

**Error Responses:**
```json
{
  "error": "string",
  "error_type": "navigation_failed|timeout|invalid_url",
  "screenshot": "string|null"
}
```

---

### Tool: `federalscout_click_element`

**Purpose:** Click an element on the current page

**Parameters:**
```json
{
  "session_id": {
    "type": "string",
    "description": "Session ID from start_discovery",
    "required": true
  },
  "selector": {
    "type": "string",
    "description": "CSS selector or text to click",
    "required": true,
    "examples": [
      "#button_id",
      ".class-name",
      "Start Estimate",
      "button:has-text('Continue')"
    ]
  },
  "selector_type": {
    "type": "string",
    "enum": ["text", "id", "css", "auto"],
    "default": "auto",
    "description": "How to interpret the selector"
  }
}
```

**Response:**
```json
{
  "success": true,
  "screenshot": "string (base64 JPEG)",
  "current_url": "string",
  "html_context": [...],
  "message": "string"
}
```

**Error Response:**
```json
{
  "success": false,
  "error": "string",
  "error_type": "element_not_found|not_clickable|timeout",
  "screenshot": "string",
  "suggestion": "string (alternative selector suggestion)"
}
```


---

### Tool: `federalscout_get_page_info`

**Purpose:** Get detailed information about current page

**Parameters:**
```json
{
  "session_id": {
    "type": "string",
    "required": true
  }
}
```

**Response:**
```json
{
  "screenshot": "string (base64 JPEG)",
  "current_url": "string",
  "page_title": "string",
  "elements": {
    "inputs": [
      {
        "type": "text|number|radio|checkbox|search",
        "id": "string",
        "name": "string",
        "class": "string",
        "visible": "boolean",
        "value": "string"
      }
    ],
    "selects": [
      {
        "id": "string",
        "name": "string",
        "options": ["string"]
      }
    ],
    "textareas": [...],
    "buttons": [
      {
        "text": "string",
        "id": "string",
        "type": "submit|button"
      }
    ]
  }
}
```

---

### Tool: `federalscout_save_page_metadata`

**Purpose:** Save discovered page metadata to session

**Parameters:**
```json
{
  "session_id": {
    "type": "string",
    "required": true
  },
  "page_metadata": {
    "type": "object",
    "required": true,
    "schema": {
      "page_number": "integer",
      "page_title": "string",
      "url_pattern": "string",
      "fields": [
        {
          "label": "string",
          "field_id": "string",
          "selector": "string",
          "field_type": "string",
          "interaction": "string",
          "required": "boolean",
          "example_value": "string",
          "notes": "string"
        }
      ],
      "continue_button": {
        "text": "string",
        "selector": "string"
      }
    }
  }
}
```

**Response:**
```json
{
  "success": true,
  "total_pages_discovered": "integer",
  "message": "string"
}
```

---

### Tool: `federalscout_complete_discovery`

**Purpose:** Finish discovery and save wizard structure to JSON

**Parameters:**
```json
{
  "session_id": {
    "type": "string",
    "required": true
  },
  "wizard_name": {
    "type": "string",
    "required": true,
    "description": "Human-readable name",
    "example": "FSA Student Aid Estimator"
  },
  "wizard_id": {
    "type": "string",
    "required": true,
    "description": "Filename slug (lowercase, hyphens)",
    "example": "fsa-estimator",
    "pattern": "^[a-z0-9-]+$"
  }
}
```

**Response:**
```json
{
  "success": true,
  "wizard_id": "string (filename: wizard_id.json)",
  "saved_to": "string (full path)",
  "wizard_structure": {
    "... complete structure for review ..."
  },
  "validation": {
    "valid": true,
    "total_pages": "integer",
    "total_fields": "integer",
    "warnings": ["string"]
  }
}
```

---

## FederalRunner Execution Tools

### Tool: `federalrunner_list_wizards`

**Purpose:** List all available wizard structures

**OAuth Scope:** `federalrunner:read`

**Parameters:** None

**Response:**
```json
{
  "wizards": [
    {
      "wizard_id": "fsa-estimator.json",
      "name": "FSA Student Aid Estimator",
      "url": "https://studentaid.gov/aid-estimator/",
      "total_pages": 6,
      "discovered_at": "2025-01-15T10:30:00Z",
      "description": "Calculate Student Aid Index (SAI)"
    }
  ],
  "count": 1
}
```

---

### Tool: `federalrunner_get_wizard_info`

**Purpose:** Get detailed information about a specific wizard

**OAuth Scope:** `federalrunner:read`

**Parameters:**
```json
{
  "wizard_id": {
    "type": "string",
    "required": true,
    "description": "Wizard filename",
    "example": "fsa-estimator.json"
  }
}
```

**Response:**
```json
{
  "wizard_id": "string",
  "name": "string",
  "url": "string",
  "total_pages": "integer",
  "discovered_at": "string (ISO 8601)",
  "pages_summary": [
    {
      "page_number": 1,
      "page_title": "Student Information",
      "field_count": 5,
      "required_fields": [
        "Date of birth",
        "Marital status",
        "State of residence",
        "Grade level"
      ]
    }
  ],
  "required_user_data": {
    "student_birthdate": {
      "description": "Student's date of birth",
      "type": "date",
      "example": "2007-05-15"
    },
    "student_state": {
      "description": "Student's state of residence",
      "type": "string",
      "example": "Illinois"
    },
    "...": "..."
  }
}
```

---

### Tool: `federalrunner_execute_wizard`

**Purpose:** Execute wizard with user-provided data

**OAuth Scope:** `federalrunner:execute`

**Parameters:**
```json
{
  "wizard_id": {
    "type": "string",
    "required": true,
    "description": "Wizard to execute",
    "example": "fsa-estimator.json"
  },
  "user_data": {
    "type": "object",
    "required": true,
    "description": "User's data for the wizard",
    "example": {
      "birth_year": "2007",
      "birth_month": "05",
      "birth_day": "15",
      "student_unmarried": true,
      "state": "Illinois",
      "grade": "freshman",
      "parent_married": true,
      "family_size": "4",
      "parent_income": "85000",
      "parent_assets": "12000",
      "student_income": "0",
      "student_assets": "0"
    }
  },
  "options": {
    "type": "object",
    "required": false,
    "properties": {
      "return_screenshots": {
        "type": "boolean",
        "default": true,
        "description": "Include screenshots in response"
      },
      "screenshot_quality": {
        "type": "integer",
        "default": 80,
        "description": "JPEG quality (1-100)"
      },
      "timeout_seconds": {
        "type": "integer",
        "default": 60,
        "description": "Maximum execution time"
      }
    }
  }
}
```

**Response (Success):**
```json
{
  "status": "success",
  "wizard_id": "fsa-estimator.json",
  "execution_time_ms": 8500,
  "results": {
    "student_aid_index": "19514",
    "federal_pell_grant_estimate": "6495",
    "eligibility": "Eligible for federal aid",
    "cost_of_attendance": "45000",
    "expected_family_contribution": "19514"
  },
  "screenshots": [
    {
      "page": 1,
      "title": "Student Information",
      "image": "base64_jpeg..."
    },
    {
      "page": 2,
      "title": "Personal Circumstances",
      "image": "base64_jpeg..."
    },
    {
      "page": "results",
      "title": "Your Results",
      "image": "base64_jpeg..."
    }
  ],
  "pages_completed": 6,
  "timestamp": "2025-01-15T14:30:00Z"
}
```

**Response (Validation Error):**
```json
{
  "status": "validation_error",
  "wizard_id": "fsa-estimator.json",
  "error": "Form validation failed on page 3",
  "page_number": 3,
  "validation_errors": [
    {
      "field": "Parent income",
      "message": "Income must be a valid number",
      "provided_value": "abc"
    }
  ],
  "screenshot": "base64_jpeg...",
  "corrective_action": "Please provide a valid numeric income amount"
}
```

**Response (Missing Data):**
```json
{
  "status": "missing_data",
  "wizard_id": "fsa-estimator.json",
  "missing_fields": [
    {
      "label": "What is the student's date of birth?",
      "field_id": "student_birthdate",
      "example": "2007-05-15",
      "required": true
    }
  ],
  "message": "Please provide the missing required information"
}
```

**Response (Execution Error):**
```json
{
  "status": "error",
  "wizard_id": "fsa-estimator.json",
  "error_type": "navigation_failed|selector_not_found|timeout|browser_error",
  "error": "string (detailed error message)",
  "page_number": 4,
  "screenshot": "base64_jpeg...",
  "recommendation": "Wizard structure may need to be re-discovered"
}
```

---

### Tool: `federalrunner_validate_user_data` (Optional)

**Purpose:** Validate user data before execution

**OAuth Scope:** `federalrunner:read`

**Parameters:**
```json
{
  "wizard_id": {
    "type": "string",
    "required": true
  },
  "user_data": {
    "type": "object",
    "required": true
  }
}
```

**Response:**
```json
{
  "valid": "boolean",
  "missing_fields": [
    {
      "label": "string",
      "field_id": "string",
      "example": "string"
    }
  ],
  "invalid_fields": [
    {
      "field_id": "string",
      "provided_value": "any",
      "expected_type": "string",
      "error": "string"
    }
  ],
  "warnings": [
    {
      "field_id": "string",
      "message": "string",
      "severity": "low|medium|high"
    }
  ]
}
```

---

## Common Response Patterns

### Success Response Structure
```json
{
  "status": "success",
  "...": "tool-specific data",
  "timestamp": "ISO 8601 timestamp"
}
```

### Error Response Structure
```json
{
  "status": "error",
  "error_type": "string (category)",
  "error": "string (human-readable message)",
  "technical_details": "string (for debugging)",
  "screenshot": "base64|null",
  "corrective_action": "string (what to do next)",
  "timestamp": "ISO 8601 timestamp"
}
```

---

## OAuth Scopes

### FederalRunner Scopes

**`federalrunner:read`**
- Grants access to: `federalrunner_list_wizards`, `federalrunner_get_wizard_info`, `federalrunner_validate_user_data`
- Description: "Read wizard information and validate data"

**`federalrunner:execute`**
- Grants access to: `federalrunner_execute_wizard`
- Description: "Execute wizards with user data"
- Requires: `federalrunner:read` (implicit)

---

## Authentication Flow (FederalRunner Only)

### Client Credentials Flow

```
1. Client requests access token from Auth0
   POST https://your-domain.auth0.com/oauth/token
   {
     "grant_type": "client_credentials",
     "client_id": "...",
     "client_secret": "...",
     "audience": "https://federalrunner-api"
   }

2. Auth0 returns access token
   {
     "access_token": "eyJ...",
     "token_type": "Bearer",
     "expires_in": 86400,
     "scope": "federalrunner:read federalrunner:execute"
   }

3. Client includes token in MCP requests
   Authorization: Bearer eyJ...

4. FederalRunner validates token
   - Verify signature using JWKS
   - Check expiration
   - Validate audience
   - Extract and verify scopes

5. Tool executes if authorized
```

---

## Tool Discovery

### MCP `tools/list` Response (FederalScout)

```json
{
  "tools": [
    {
      "name": "federalscout_start_discovery",
      "description": "Begin wizard structure discovery session",
      "inputSchema": {
        "type": "object",
        "properties": {
          "url": {
            "type": "string",
            "description": "Starting URL of the government wizard"
          }
        },
        "required": ["url"]
      }
    },
    {
      "name": "federalscout_click_element",
      "description": "Click an element on the current page",
      "inputSchema": {...}
    }
  ]
}
```

### MCP `tools/list` Response (FederalRunner)

```json
{
  "tools": [
    {
      "name": "federalrunner_list_wizards",
      "description": "List all available government wizard structures",
      "inputSchema": {
        "type": "object",
        "properties": {},
        "required": []
      }
    },
    {
      "name": "federalrunner_get_wizard_info",
      "description": "Get detailed information about a specific wizard",
      "inputSchema": {...}
    },
    {
      "name": "federalrunner_execute_wizard",
      "description": "Execute a wizard with user-provided data",
      "inputSchema": {...}
    }
  ]
}
```

---

## Rate Limiting (FederalRunner)

**Per-client limits:**
- `federalrunner_list_wizards`: 100 requests/hour
- `federalrunner_get_wizard_info`: 100 requests/hour
- `federalrunner_execute_wizard`: 20 requests/hour

**Rate limit response:**
```json
{
  "error": "rate_limit_exceeded",
  "message": "Rate limit exceeded for federalrunner_execute_wizard",
  "retry_after_seconds": 3600,
  "limit": 20,
  "reset_at": "2025-01-15T15:00:00Z"
}
```

---

## Success Criteria

MCP tools are successful when:
1. ✅ All tools return valid JSON responses
2. ✅ Schemas match specifications exactly
3. ✅ Error responses are structured and actionable
4. ✅ Screenshots are properly encoded and sized
5. ✅ OAuth scopes are enforced correctly
6. ✅ Tools are discoverable via `tools/list`
7. ✅ All responses include timestamps
8. ✅ Documentation matches implementation

---

## References

- MCP Specification: https://modelcontextprotocol.io/specification
- Discovery Requirements: `requirements/discovery/DISCOVERY_REQUIREMENTS.md`
- Execution Requirements: `requirements/execution/EXECUTION_REQUIREMENTS.md`
- MDCalc MCP Implementation: Reference for HTTP+OAuth patterns