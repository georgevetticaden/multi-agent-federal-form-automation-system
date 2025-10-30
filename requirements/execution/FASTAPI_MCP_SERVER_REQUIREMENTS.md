# FederalRunner FastAPI MCP Server Requirements

**Version:** 1.0.0
**Status:** Ready for Implementation
**Last Updated:** 2025-10-18

---

## Overview

This document defines the technical requirements for implementing the FederalRunner FastAPI MCP server with OAuth 2.1 authentication. The server implements Model Context Protocol (MCP) 2025-06-18 specification for providing federal form automation to AI assistants like Claude.

**Key Pattern**: Implement FastAPI server with MCP Protocol 2025-06-18, OAuth 2.1, and selective authentication for FederalRunner's execution tools.

---

## REQ-SERVER-001: Server Architecture

### Requirement

FastAPI server MUST implement MCP Protocol 2025-06-18 with Streamable HTTP transport (POST-only, no SSE streaming).

### Architecture Components

```python
# File: mcp-servers/federalrunner-mcp/src/server.py

1. FastAPI Application with Lifespan Management
2. OAuth 2.1 Authentication (selective by method)
3. MCP Protocol Handler
4. Session Management
5. Tool Execution Router
6. CORS Middleware
7. Request Logging Middleware
```

### Transport Layer

**Streamable HTTP (POST-only)**:
- HEAD / → 200 with MCP-Protocol-Version header (protocol discovery)
- GET / → 405 Method Not Allowed (signals POST-only transport)
- POST / → Main MCP endpoint (all methods)
- DELETE / → Session termination
- GET /health → Health check (no auth)
- GET /.well-known/oauth-protected-resource → OAuth metadata (DCR)

---

## REQ-SERVER-002: Selective Authentication

### Requirement

Authentication MUST be selectively applied based on MCP method type, per MCP specification.

### Authentication Strategy

| MCP Method | Authentication Required | Validation Type |
|------------|------------------------|-----------------|
| `initialize` | ❌ NO | None (client discovers OAuth config) |
| `notifications/initialized` | ⚠️ SESSION ONLY | Session ID validation only |
| `tools/list` | ✅ FULL | OAuth token + session validation |
| `tools/call` | ✅ FULL | OAuth token + session validation |

### Implementation Pattern

```python
async def mcp_endpoint(request: Request):
    """Main MCP handler with selective authentication."""
    body = await request.json()
    method = body.get('method')

    if method == 'initialize':
        # NO AUTHENTICATION
        # Generate session ID
        session_id = str(uuid.uuid4())
        sessions[session_id] = {...}

        # Return capabilities + OAuth config
        return {
            'protocolVersion': '2025-06-18',
            'capabilities': {'tools': {}},
            'serverInfo': {...}
        }

    elif method == 'notifications/initialized':
        # SESSION VALIDATION ONLY (no OAuth token)
        session_id = request.headers.get('mcp-session-id')
        validate_session(session_id, request)
        return Response(status_code=202)  # Accepted

    elif method == 'tools/list':
        # FULL AUTHENTICATION
        token_payload = await verify_token_manual(request)
        scopes = get_token_scopes(token_payload)
        session_id = request.headers.get('mcp-session-id')
        validate_session(session_id, request)

        tools = get_tools()
        return {'tools': tools}

    elif method == 'tools/call':
        # FULL AUTHENTICATION
        token_payload = await verify_token_manual(request)
        scopes = get_token_scopes(token_payload)
        session_id = request.headers.get('mcp-session-id')
        validate_session(session_id, request)

        tool_name = params.get('name')
        arguments = params.get('arguments', {})
        result = await execute_tool(tool_name, arguments, scopes)
        return result
```

### Rationale

Per MCP spec, `initialize` must be accessible without auth so clients can discover OAuth configuration. This enables Claude Android to learn how to authenticate before requesting protected resources.

---

## REQ-SERVER-003: Tool Definitions

### Requirement

Server MUST define 3 FederalRunner MCP tools with proper input schemas and OAuth scope requirements.

### Tool Specifications

#### Tool 1: federalrunner_list_wizards

```python
{
    'name': 'federalrunner_list_wizards',
    'description': (
        'Get the complete list of available federal form wizards. '
        'Returns wizard metadata including ID, name, URL, page count, and estimated completion time. '
        'Use this to discover which forms are available for execution. '
        'Currently supported: FSA Student Aid Estimator. '
        'Future: Social Security Retirement, IRS Tax Withholding, Medicare Plan Finder.'
    ),
    'inputSchema': {
        'type': 'object',
        'properties': {},
        'required': []
    }
}
```

**Required Scope**: `federalrunner:read`

**Implementation**:
```python
# Call execution_tools.federalrunner_list_wizards()
# Returns: List of wizard metadata
```

#### Tool 2: federalrunner_get_wizard_info

```python
{
    'name': 'federalrunner_get_wizard_info',
    'description': (
        'Get detailed information about a specific wizard, including its User Data Schema (THE CONTRACT). '
        'The schema defines exactly what data is required to execute the wizard. '
        'YOU must read this schema to understand what questions to ask the user. '
        'The schema includes field types, validation patterns, required fields, and conditional dependencies. '
        'This enables schema-first data collection where you extract, map, and transform user input '
        'to match the schema format before calling federalrunner_execute_wizard.'
    ),
    'inputSchema': {
        'type': 'object',
        'properties': {
            'wizard_id': {
                'type': 'string',
                'description': (
                    'Wizard identifier (e.g., "fsa-estimator" for FSA Student Aid Estimator). '
                    'Get wizard IDs from federalrunner_list_wizards results.'
                )
            }
        },
        'required': ['wizard_id']
    }
}
```

**Required Scope**: `federalrunner:read`

**Implementation**:
```python
# Call execution_tools.federalrunner_get_wizard_info(wizard_id)
# Returns: Wizard metadata + User Data Schema (JSON Schema draft-07)
```

#### Tool 3: federalrunner_execute_wizard

```python
{
    'name': 'federalrunner_execute_wizard',
    'description': (
        'Execute a federal form wizard with provided user data. '
        'This is an ATOMIC, MECHANICAL tool - it validates data against the schema, '
        'launches a headless browser, fills all form fields sequentially, and extracts results. '
        'YOU must first call federalrunner_get_wizard_info to get the schema, then collect '
        'all required data from the user (with proper transformations), and finally call this tool. '
        'Returns execution results with screenshots showing each page filled. '
        'If execution fails, examine the error screenshot to understand what went wrong (visual validation loop).'
    ),
    'inputSchema': {
        'type': 'object',
        'properties': {
            'wizard_id': {
                'type': 'string',
                'description': 'Wizard identifier (e.g., "fsa-estimator")'
            },
            'user_data': {
                'type': 'object',
                'description': (
                    'User data matching the wizard\'s User Data Schema. '
                    'All required fields must be present and properly formatted. '
                    'Field names must match schema property names (field_id). '
                    'Values must match schema types and validation patterns. '
                    'YOU are responsible for collecting and transforming this data correctly.'
                ),
                'additionalProperties': True
            }
        },
        'required': ['wizard_id', 'user_data']
    }
}
```

**Required Scope**: `federalrunner:execute`

**Implementation**:
```python
# Call execution_tools.federalrunner_execute_wizard(wizard_id, user_data)
# Returns: {
#   'success': bool,
#   'wizard_id': str,
#   'results': dict (if success),
#   'screenshots': list[base64],  # All pages + result
#   'pages_completed': int,
#   'execution_time_ms': int,
#   'error': str (if failure),
#   'validation_errors': dict (if schema validation failed)
# }
```

### Tool Execution Function

```python
async def execute_tool(tool_name: str, arguments: Dict, scopes: list) -> Dict:
    """
    Execute the specified FederalRunner tool with given arguments.

    Validates scopes and delegates to execution_tools module.

    Returns:
        Dict containing 'content' with tool results in MCP format
    """
    if tool_name == 'federalrunner_list_wizards':
        require_scope('federalrunner:read', scopes)

        wizards = await federalrunner_list_wizards()

        return {
            'content': [
                {
                    'type': 'text',
                    'text': json.dumps({
                        'success': True,
                        'count': len(wizards),
                        'wizards': wizards
                    }, indent=2)
                }
            ]
        }

    elif tool_name == 'federalrunner_get_wizard_info':
        require_scope('federalrunner:read', scopes)

        wizard_id = arguments.get('wizard_id')
        info = await federalrunner_get_wizard_info(wizard_id)

        # Return both metadata and schema
        return {
            'content': [
                {
                    'type': 'text',
                    'text': json.dumps({
                        'success': True,
                        'wizard_id': info['wizard_id'],
                        'wizard_name': info['wizard_name'],
                        'url': info['url'],
                        'page_count': info['page_count'],
                        'schema': info['schema']  # THE CONTRACT
                    }, indent=2)
                }
            ]
        }

    elif tool_name == 'federalrunner_execute_wizard':
        require_scope('federalrunner:execute', scopes)

        wizard_id = arguments.get('wizard_id')
        user_data = arguments.get('user_data', {})

        result = await federalrunner_execute_wizard(wizard_id, user_data)

        # Build response with screenshots
        content = []

        # Add screenshots as image content
        if result.get('screenshots'):
            for screenshot_base64 in result['screenshots']:
                content.append({
                    'type': 'image',
                    'data': screenshot_base64,
                    'mimeType': 'image/jpeg'
                })

        # Add text result (without base64 to avoid duplication)
        text_result = {k: v for k, v in result.items() if k != 'screenshots'}
        text_result['screenshots_included'] = len(result.get('screenshots', []))

        content.append({
            'type': 'text',
            'text': json.dumps(text_result, indent=2)
        })

        return {'content': content}
```

---

## REQ-SERVER-004: Session Management

### Requirement

Server MUST maintain MCP session state for protocol compliance.

### Implementation

```python
# Global session storage
sessions: Dict[str, Dict[str, Any]] = {}  # session_id -> session data
session_initialized: Dict[str, bool] = {}  # session_id -> initialization status

def validate_session(session_id: str, request: Request) -> None:
    """
    Validate that a session ID exists and is properly initialized.

    Raises:
        HTTPException: If session is invalid or not found
    """
    if not session_id:
        raise HTTPException(
            status_code=400,
            detail="Missing MCP-Session-ID header"
        )

    if session_id not in sessions:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid session ID: {session_id}"
        )
```

### Session Lifecycle

1. **Create**: On `initialize` request, generate UUID
2. **Mark Ready**: Set `session_initialized[session_id] = True`
3. **Validate**: Check exists for all subsequent requests
4. **Cleanup**: Remove on `DELETE /` or timeout

---

## REQ-SERVER-005: CORS Configuration

### Requirement

Server MUST allow cross-origin requests from Claude.ai and Claude Mobile.

### Implementation

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Public API - any origin can call
    allow_credentials=False,  # Bearer tokens don't need credentials flag
    allow_methods=["GET", "POST", "DELETE", "HEAD", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "MCP-Protocol-Version", "MCP-Session-ID"],
    expose_headers=["MCP-Protocol-Version", "MCP-Session-ID", "WWW-Authenticate"],
)
```

### Rationale

- **allow_origins=["*"]**: Public MCP server, accessed from web and mobile
- **allow_credentials=False**: Using Bearer tokens in Authorization header, not cookies
- **expose_headers**: Allow client to read MCP protocol headers

---

## REQ-SERVER-006: Request Logging Middleware

### Requirement

Server MUST log all incoming requests for debugging Claude.ai connectivity issues.

### Implementation

```python
@app.middleware("http")
async def log_all_requests(request: Request, call_next):
    """Log all incoming requests to debug Claude.ai connectivity."""
    logger.info(f"📨 Incoming request: {request.method} {request.url.path}")

    # Log MCP headers
    protocol_version = request.headers.get('mcp-protocol-version') or request.headers.get('MCP-Protocol-Version')
    session_id = request.headers.get('mcp-session-id') or request.headers.get('MCP-Session-ID')

    logger.info(f"   MCP-Protocol-Version: {protocol_version or 'NOT PRESENT'}")
    logger.info(f"   MCP-Session-ID: {session_id or 'NOT PRESENT'}")

    # Log body for POST requests
    if request.method == "POST":
        body = await request.body()
        if body:
            try:
                body_json = json.loads(body.decode())
                logger.info(f"   Request body: {json.dumps(body_json, indent=2)}")
            except:
                pass
        # Re-create request with body for downstream handlers
        async def receive():
            return {"type": "http.request", "body": body}
        request = Request(request.scope, receive)

    response = await call_next(request)
    logger.info(f"📤 Response: {response.status_code}")

    return response
```

---

## REQ-SERVER-007: Lifespan Management

### Requirement

Server MUST initialize PlaywrightClient during startup and cleanup during shutdown.

### Implementation

```python
from contextlib import asynccontextmanager

playwright_client: Optional[PlaywrightClient] = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for FastAPI.
    Initialize and cleanup resources.
    """
    global playwright_client

    # Startup
    logger.info("="*60)
    logger.info("FederalRunner MCP Server Starting")
    logger.info("="*60)
    logger.info(f"Environment: {'Cloud Run' if settings.MCP_SERVER_URL.startswith('https') else 'Local Development'}")
    logger.info(f"Auth0 Domain: {settings.AUTH0_DOMAIN}")
    logger.info(f"API Audience: {settings.AUTH0_API_AUDIENCE}")
    logger.info(f"Wizards Directory: {settings.FEDERALRUNNER_WIZARDS_DIR}")
    logger.info(f"Browser: {settings.FEDERALRUNNER_BROWSER_TYPE}")
    logger.info(f"Headless: {settings.FEDERALRUNNER_HEADLESS}")

    logger.info("Initializing PlaywrightClient...")
    playwright_client = PlaywrightClient(
        headless=settings.FEDERALRUNNER_HEADLESS,
        browser_type=settings.FEDERALRUNNER_BROWSER_TYPE
    )

    try:
        await playwright_client.initialize()
        logger.info("✅ PlaywrightClient initialized successfully")
        logger.info("✅ FederalRunner MCP Server ready to accept requests")
    except Exception as e:
        logger.error(f"❌ Failed to initialize PlaywrightClient: {e}")
        raise

    yield

    # Shutdown
    logger.info("="*60)
    logger.info("FederalRunner MCP Server Shutting Down")
    logger.info("="*60)
    if playwright_client:
        logger.info("Cleaning up PlaywrightClient...")
        await playwright_client.close()
        logger.info("✅ PlaywrightClient cleaned up")
    logger.info("✅ FederalRunner MCP Server stopped")


# Create FastAPI app with lifespan
app = FastAPI(
    title="FederalRunner MCP Server",
    description="Remote MCP server for federal form automation with OAuth 2.1",
    version="1.0.0",
    lifespan=lifespan
)
```

---

## REQ-SERVER-008: Environment Configuration

### Requirement

Server MUST load configuration from environment variables via config.py.

### Required Environment Variables

```python
# Auth0 Configuration
AUTH0_DOMAIN=your-tenant.us.auth0.com
AUTH0_ISSUER=https://your-tenant.us.auth0.com/
AUTH0_API_AUDIENCE=https://your-service.run.app

# MCP Server Configuration
MCP_SERVER_URL=https://your-service.run.app
PORT=8080

# FederalRunner Configuration
FEDERALRUNNER_WIZARDS_DIR=/app/wizards          # Cloud Run
FEDERALRUNNER_BROWSER_TYPE=webkit               # FSA compatibility
FEDERALRUNNER_HEADLESS=true                     # Production
```

### Config Class Updates

```python
# Add to src/config.py

from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Existing FederalRunner config...
    FEDERALRUNNER_WIZARDS_DIR: Optional[Path] = None
    FEDERALRUNNER_HEADLESS: bool = False
    FEDERALRUNNER_BROWSER_TYPE: str = "chromium"

    # NEW: Auth0 Configuration
    AUTH0_DOMAIN: str
    AUTH0_ISSUER: str
    AUTH0_API_AUDIENCE: str

    # NEW: MCP Server Configuration
    MCP_SERVER_URL: str
    PORT: int = 8080

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )
```

---

## REQ-SERVER-009: Error Handling

### Requirement

Server MUST return proper JSON-RPC error responses per MCP specification.

### Error Response Format

```python
{
    'jsonrpc': '2.0',
    'id': request_id,
    'error': {
        'code': -32603,  # Internal error
        'message': 'Error message here'
    }
}
```

### Error Handling Pattern

```python
try:
    # Handle MCP request
    ...
except HTTPException:
    # Re-raise HTTP exceptions (from token validation)
    raise
except Exception as e:
    logger.error(f"Error handling MCP request: {e}")

    response = JSONResponse(
        status_code=200,  # JSON-RPC uses 200 even for errors
        content={
            'jsonrpc': '2.0',
            'id': request_id if 'request_id' in locals() else None,
            'error': {
                'code': -32603,
                'message': f'Internal error: {str(e)}'
            }
        }
    )

    # Always include MCP headers
    response.headers['MCP-Protocol-Version'] = '2025-06-18'
    if session_id:
        response.headers['MCP-Session-ID'] = session_id

    return response
```

---

## Implementation Checklist

### Phase 1: Core Server Structure
- [ ] Create `src/server.py` with FastAPI app
- [ ] Implement lifespan management
- [ ] Add CORS middleware
- [ ] Add request logging middleware
- [ ] Create health check endpoint

### Phase 2: MCP Protocol Implementation
- [ ] Implement HEAD / endpoint (protocol discovery)
- [ ] Implement GET / endpoint (405 Method Not Allowed)
- [ ] Implement POST / endpoint (main MCP handler)
- [ ] Implement DELETE / endpoint (session termination)
- [ ] Add session management (create, validate, cleanup)

### Phase 3: Tool Definitions
- [ ] Implement `get_tools()` function with 3 tool definitions
- [ ] Implement `execute_tool()` function
- [ ] Call execution_tools functions correctly
- [ ] Format responses with MCP content blocks (text + images)

### Phase 4: OAuth Integration
- [ ] Implement `auth.py` with OAuth 2.1 token validation
- [ ] Implement selective authentication in mcp_endpoint
- [ ] Add /.well-known/oauth-protected-resource endpoint
- [ ] Test token validation

### Phase 5: Local Testing
- [ ] Test without OAuth (comment out auth checks)
- [ ] Test with OAuth (use M2M token from Auth0)
- [ ] Verify all 3 tools work
- [ ] Check MCP protocol compliance

---

## Success Criteria

✅ Server starts successfully with lifespan management
✅ Health endpoint returns 200
✅ OAuth metadata endpoint returns correct Auth0 config
✅ MCP protocol discovery works (HEAD /)
✅ Sessions are created on initialize
✅ Tools require proper OAuth scopes
✅ All 3 tools execute correctly
✅ Screenshots are returned as image content
✅ Error responses follow JSON-RPC format
✅ CORS allows Claude.ai/mobile access

---

## References

- **MCP Specification**: https://modelcontextprotocol.io/specification/2025-06-18
- **FastAPI Docs**: https://fastapi.tiangolo.com/
- **OAuth 2.1 Spec**: https://oauth.net/2.1/
- **Execution Tools**: `mcp-servers/federalrunner-mcp/src/execution_tools.py`
