"""
FastAPI server for FederalRunner MCP with OAuth 2.1 authentication.

This server implements the Model Context Protocol (MCP) specification 2025-06-18
for providing automated execution of federal form wizards to AI assistants like Claude.

ARCHITECTURE:
    - Transport: Streamable HTTP (POST-only, no SSE streaming)
    - Authentication: OAuth 2.1 via Auth0 with Dynamic Client Registration (RFC 7591)
    - Protocol: MCP 2025-06-18 with selective authentication
    - Deployment: Google Cloud Run (serverless containers)

AUTHENTICATION STRATEGY:
    Per MCP specification, authentication is selectively applied based on method:

    - initialize: NO auth required (client discovers OAuth config)
    - notifications/initialized: Session validation only (no OAuth token)
    - tools/list: FULL auth (OAuth token + session validation)
    - tools/call: FULL auth (OAuth token + session validation)

    This ensures MCP protocol compliance while maintaining security.

ENDPOINTS:
    GET /health - Health check (no auth)
    GET /.well-known/oauth-protected-resource - OAuth metadata for DCR (RFC 9728)
    HEAD / - MCP protocol discovery (returns MCP-Protocol-Version header)
    GET / - Returns 405 Method Not Allowed (signals POST-only transport)
    POST / - MCP JSON-RPC endpoint (all methods: initialize, tools/list, etc.)
    DELETE / - Session termination (session validation only)

SUCCESSFUL CONNECTION SEQUENCE:
    1. HEAD / -> 200 with MCP-Protocol-Version header
    2. GET /.well-known/oauth-protected-resource -> OAuth config
    3. POST / initialize -> Session created (no auth required)
    4. POST / notifications/initialized -> 202 Accepted (session validation only)
    5. GET / -> 405 Method Not Allowed (transport detection)
    6. User authenticates via Auth0 OAuth flow
    7. POST / tools/list -> 200 with tools (OAuth + session validated)
    8. POST / tools/call -> Wizard execution (OAuth + session validated)

For deployment instructions, see requirements/execution/EXECUTION_DEPLOYMENT_REQUIREMENTS.md
For Auth0 setup, see requirements/execution/AUTH0_CONFIGURATION_REQUIREMENTS.md
"""

import json
from typing import Dict, Any, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse, Response
from fastapi.middleware.cors import CORSMiddleware

from .config import get_config
from .auth import verify_token_manual, get_token_scopes, require_scope
from .execution_tools import federalrunner_list_wizards, federalrunner_get_wizard_info, federalrunner_execute_wizard
from .playwright_client import PlaywrightClient
from .logging_config import get_logger

# Setup logger for this module
logger = get_logger(__name__)

# Global configuration
config = get_config()

# Global Playwright client instance
playwright_client: Optional[PlaywrightClient] = None

# Session management
sessions: Dict[str, Dict[str, Any]] = {}  # session_id -> session data
session_initialized: Dict[str, bool] = {}  # session_id -> initialization status


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
    logger.info(f"Environment: {'Cloud Run' if config.mcp_server_url.startswith('https') else 'Local Development'}")
    logger.info(f"Auth0 Domain: {config.auth0_domain}")
    logger.info(f"API Audience: {config.auth0_api_audience}")
    logger.info(f"Server URL: {config.mcp_server_url}")
    logger.info(f"Port: {config.port}")
    logger.info(f"Wizards Directory: {config.wizards_dir}")
    logger.info(f"Browser: {config.browser_type} (headless={config.headless})")

    logger.info("Initializing Playwright client...")
    playwright_client = PlaywrightClient(config)

    try:
        await playwright_client.initialize()
        logger.info(" Playwright client initialized successfully")
        logger.info(" FederalRunner MCP Server ready to accept requests")
    except Exception as e:
        logger.error(f"L Failed to initialize Playwright client: {e}")
        raise

    yield

    # Shutdown
    logger.info("="*60)
    logger.info("FederalRunner MCP Server Shutting Down")
    logger.info("="*60)
    if playwright_client:
        logger.info("Cleaning up Playwright client...")
        await playwright_client.cleanup()
        logger.info(" Playwright client cleaned up")
    logger.info(" FederalRunner MCP Server stopped")


# Create FastAPI app
app = FastAPI(
    title="FederalRunner MCP Server",
    description="Remote MCP server for federal form wizard automation with OAuth 2.1",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
# Note: allow_credentials=False because we use Bearer tokens in Authorization header, not cookies
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Public API - any origin can call
    allow_credentials=False,  # Bearer tokens don't need credentials flag
    allow_methods=["GET", "POST", "DELETE", "HEAD", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "MCP-Protocol-Version", "MCP-Session-ID"],
    expose_headers=["MCP-Protocol-Version", "MCP-Session-ID", "WWW-Authenticate"],  # Expose MCP headers to client
)


# Add request logging middleware to debug Claude.ai connection issues
@app.middleware("http")
async def log_all_requests(request: Request, call_next):
    """Log all incoming requests to debug Claude.ai connectivity."""
    logger.info(f"==> Incoming request: {request.method} {request.url.path}")

    # Log critical MCP headers at INFO level (not DEBUG)
    protocol_version = request.headers.get('mcp-protocol-version') or request.headers.get('MCP-Protocol-Version')
    session_id = request.headers.get('mcp-session-id') or request.headers.get('MCP-Session-ID')

    logger.info(f"   MCP-Protocol-Version: {protocol_version or 'NOT PRESENT'}")
    logger.info(f"   MCP-Session-ID: {session_id or 'NOT PRESENT'}")
    logger.debug(f"   All Headers: {dict(request.headers)}")

    # Log body for POST requests (helps debug what Claude is sending)
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
    logger.info(f"==> Response: {response.status_code}")

    # Log MCP headers in response
    response_protocol = response.headers.get('MCP-Protocol-Version')
    response_session = response.headers.get('MCP-Session-ID')
    if response_protocol or response_session:
        logger.info(f"   Response MCP-Protocol-Version: {response_protocol or 'not set'}")
        logger.info(f"   Response MCP-Session-ID: {response_session or 'not set'}")

    return response


@app.get("/health")
async def health_check():
    """Health check endpoint (no authentication required)."""
    logger.debug("Health check requested")
    return {
        "status": "healthy",
        "service": "federalrunner-mcp-server",
        "version": "1.0.0"
    }


@app.get("/.well-known/oauth-protected-resource")
async def oauth_metadata():
    """
    OAuth Protected Resource Metadata (RFC 9728).

    Required for Claude to discover Auth0 as the authorization server
    and initiate Dynamic Client Registration (DCR).

    This is how Claude Android discovers how to authenticate.
    """
    logger.info("OAuth metadata requested (for DCR discovery)")
    logger.debug(f"Returning Auth0 domain: {config.auth0_domain}")

    return {
        "resource": config.mcp_server_url,
        "authorization_servers": [f"https://{config.auth0_domain}"],
        "bearer_methods_supported": ["header"],
        "scopes_supported": ["federalrunner:read", "federalrunner:execute"]
    }


# Session validation helper
def validate_session(session_id: str, request: Request) -> None:
    """
    Validate that a session ID exists and is properly initialized.

    Args:
        session_id: Session ID from Mcp-Session-Id header
        request: FastAPI Request object (for logging)

    Raises:
        HTTPException: If session is invalid or not found
    """
    if not session_id:
        logger.error("Missing MCP-Session-ID header")
        raise HTTPException(
            status_code=400,
            detail="Missing MCP-Session-ID header"
        )

    if session_id not in sessions:
        logger.error(f"Session not found: {session_id}")
        raise HTTPException(
            status_code=400,
            detail=f"Invalid session ID: {session_id}"
        )

    logger.debug(f"Session validated: {session_id}")


# MCP protocol discovery endpoint
@app.head("/")
async def mcp_head():
    """
    HEAD endpoint for MCP protocol discovery.
    Claude.ai uses this to check if server supports MCP before attempting connection.
    """
    return Response(
        status_code=200,
        headers={
            "MCP-Protocol-Version": "2025-06-18",
            "Content-Type": "application/json"
        }
    )


# MCP endpoint at root path (/) - required by Claude.ai
# Claude.ai sends requests to / after OAuth
@app.post("/")
async def mcp_root_endpoint(request: Request):
    """
    MCP endpoint at root path - delegates to main handler.

    NOTE: Authentication is handled INSIDE mcp_endpoint() based on method type.
    Per MCP spec, 'initialize' and 'notifications/initialized' do NOT require OAuth,
    while tool operations (tools/list, tools/call) DO require OAuth.
    """
    return await mcp_endpoint(request)


@app.get("/")
async def mcp_get_not_supported():
    """
    SSE streaming not supported - use POST-only Streamable HTTP transport.

    Returns 405 Method Not Allowed (not 501) to signal this endpoint only accepts POST.
    Per MCP spec: 405 tells Claude "this server is POST-only, proceed with connection"
    whereas 501 tells Claude "this server is broken, terminate session".
    """
    return JSONResponse(
        status_code=405,  # Method Not Allowed (use 405, not 501!)
        content={
            "jsonrpc": "2.0",
            "error": {
                "code": -32000,
                "message": "Method Not Allowed. Use POST for Streamable HTTP transport."
            },
            "id": None
        },
        headers={
            "MCP-Protocol-Version": "2025-06-18",
            "Allow": "POST, HEAD, DELETE",  # Tell client which methods ARE supported
            "Content-Type": "application/json"
        }
    )


@app.delete("/")
async def mcp_delete_session(request: Request):
    """
    DELETE endpoint for session termination.

    Per MCP spec, clients can send DELETE to terminate sessions.

    Authentication Strategy:
    - Requires valid session (must exist)
    - Does NOT require OAuth token (session termination should work even if token expired)
    """
    session_id = request.headers.get("mcp-session-id") or request.headers.get("MCP-Session-ID")
    logger.info(f"Session termination requested: {session_id}")

    # Validate session exists (but don't require OAuth token for cleanup)
    if session_id:
        validate_session(session_id, request)

        # Clean up session state
        if session_id in sessions:
            del sessions[session_id]
            logger.info(f"Removed session data for: {session_id}")
        if session_id in session_initialized:
            del session_initialized[session_id]
            logger.info(f"Removed initialization state for: {session_id}")
    else:
        logger.warning("DELETE request without session ID - nothing to clean up")

    # Echo session headers even on DELETE for consistency
    response = Response(status_code=204)
    response.headers['MCP-Protocol-Version'] = '2025-06-18'
    if session_id:
        response.headers['MCP-Session-ID'] = session_id

    return response


async def mcp_endpoint(request: Request):
    """
    MCP endpoint handler (POST-only Streamable HTTP transport).

    Implements MCP protocol version 2025-06-18.
    Accepts JSON-RPC 2.0 messages via POST and returns single JSON responses.

    Per MCP spec: https://modelcontextprotocol.io/specification/2025-06-18/basic/transports

    AUTHENTICATION STRATEGY:
    - initialize: NO auth required (returns capabilities including OAuth config)
    - notifications/initialized: Session ID validation only (no OAuth token)
    - tools/list, tools/call: FULL OAuth token + session validation required
    """
    try:
        # Parse JSON-RPC request
        body = await request.json()
        request_id = body.get('id')
        method = body.get('method')
        params = body.get('params', {})

        logger.info(f"MCP request: method={method}, id={request_id}")

        # Handle different MCP methods
        if method == 'initialize':
            # NO AUTHENTICATION REQUIRED for initialize
            # Per MCP spec: initialize must be accessible without auth
            # so client can discover OAuth configuration
            logger.info("Handling initialize request")

            # Generate session ID for this connection
            import uuid
            session_id = str(uuid.uuid4())

            # Create session and mark as initialized
            sessions[session_id] = {
                'created_at': __import__('datetime').datetime.utcnow(),
                'client_info': params.get('clientInfo', {})
            }
            session_initialized[session_id] = True  # Session ready for use

            response = JSONResponse({
                'jsonrpc': '2.0',
                'id': request_id,
                'result': {
                    'protocolVersion': '2025-06-18',  # Match Claude.ai's version
                    'capabilities': {
                        'tools': {}  # Supports tools primitive, no optional sub-features (listChanged)
                    },
                    'serverInfo': {
                        'name': 'federalrunner-mcp-server',
                        'title': 'FederalRunner - Federal Form Wizard Automation',
                        'version': '1.0.0'
                    }
                }
            })

            # Set MCP headers in response
            response.headers['MCP-Session-ID'] = session_id
            response.headers['MCP-Protocol-Version'] = '2025-06-18'
            logger.info(f"Created MCP session: {session_id} (fully initialized)")

            return response

        elif method == 'notifications/initialized':
            # SESSION VALIDATION ONLY (no OAuth token required)
            # Client is confirming it received initialize response and is ready
            # At this point, client may not have OAuth token yet
            logger.info("Received initialized notification")

            # Get session ID from request header
            session_id = request.headers.get('mcp-session-id') or request.headers.get('MCP-Session-ID')

            # Validate session exists (lightweight security check)
            validate_session(session_id, request)

            # Mark session as fully initialized
            session_initialized[session_id] = True
            logger.info(f" Session {session_id} is now FULLY INITIALIZED")

            # Return 202 Accepted (per MCP spec for notifications with id: null)
            # 202 = "Acknowledged receipt of notification, no response body"
            response = Response(status_code=202)
            response.headers['MCP-Protocol-Version'] = '2025-06-18'
            response.headers['MCP-Session-ID'] = session_id

            return response

        elif method == 'tools/list':
            # FULL AUTHENTICATION REQUIRED: OAuth token + session validation
            logger.info("Listing available tools (requires authentication)")

            # Validate OAuth token
            token_payload = await verify_token_manual(request)
            scopes = get_token_scopes(token_payload)
            logger.info(f"Token scopes: {scopes}")

            # Validate session
            session_id = request.headers.get('mcp-session-id') or request.headers.get('MCP-Session-ID')
            validate_session(session_id, request)

            # List available tools (filtered by scopes if needed)
            tools = get_tools()
            logger.info(f"Returning {len(tools)} tools")

            response = JSONResponse({
                'jsonrpc': '2.0',
                'id': request_id,
                'result': {
                    'tools': tools
                }
            })

            # Add MCP headers to response
            response.headers['MCP-Protocol-Version'] = '2025-06-18'
            response.headers['MCP-Session-ID'] = session_id

            return response

        elif method == 'tools/call':
            # FULL AUTHENTICATION REQUIRED: OAuth token + session validation
            tool_name = params.get('name')
            arguments = params.get('arguments', {})
            logger.info(f"Calling tool: {tool_name} (requires authentication)")
            logger.debug(f"Tool arguments: {arguments}")

            # Validate OAuth token
            token_payload = await verify_token_manual(request)
            scopes = get_token_scopes(token_payload)
            logger.info(f"Token scopes: {scopes}")

            # Validate session
            session_id = request.headers.get('mcp-session-id') or request.headers.get('MCP-Session-ID')
            validate_session(session_id, request)

            # Execute tool with scope validation
            result = await execute_tool(tool_name, arguments, scopes)

            logger.info(f"Tool {tool_name} completed successfully")

            response = JSONResponse({
                'jsonrpc': '2.0',
                'id': request_id,
                'result': result
            })

            # Add MCP headers to response
            response.headers['MCP-Protocol-Version'] = '2025-06-18'
            response.headers['MCP-Session-ID'] = session_id

            return response

        else:
            # Method not found
            logger.warning(f"Unknown method requested: {method}")

            # Get session ID from request
            session_id = request.headers.get('mcp-session-id') or request.headers.get('MCP-Session-ID')

            response = JSONResponse(
                status_code=200,
                content={
                    'jsonrpc': '2.0',
                    'id': request_id,
                    'error': {
                        'code': -32601,
                        'message': f'Method not found: {method}'
                    }
                }
            )

            # Add MCP headers even to error responses
            response.headers['MCP-Protocol-Version'] = '2025-06-18'
            if session_id:
                response.headers['MCP-Session-ID'] = session_id

            return response

    except HTTPException:
        # Re-raise HTTP exceptions (from token validation)
        raise

    except Exception as e:
        logger.error(f"Error handling MCP request: {e}")

        # Try to get session ID even in error case
        session_id = None
        try:
            session_id = request.headers.get('mcp-session-id') or request.headers.get('MCP-Session-ID')
        except:
            pass

        response = JSONResponse(
            status_code=200,
            content={
                'jsonrpc': '2.0',
                'id': request_id if 'request_id' in locals() else None,
                'error': {
                    'code': -32603,
                    'message': f'Internal error: {str(e)}'
                }
            }
        )

        # Add MCP headers even to error responses
        response.headers['MCP-Protocol-Version'] = '2025-06-18'
        if session_id:
            response.headers['MCP-Session-ID'] = session_id

        return response


def get_tools() -> list:
    """
    Return available FederalRunner MCP tools.

    These are atomic, mechanical operations. Claude handles ALL intelligence,
    data collection, and validation. The tools simply load schemas, validate data,
    and execute wizards.
    """
    return [
        {
            'name': 'federalrunner_list_wizards',
            'description': (
                'List all available federal form wizards that can be executed. '
                'Returns wizard metadata including ID, name, URL, page count, and discovery date. '
                'Call this first to see what wizards are available before requesting wizard info or execution.'
            ),
            'inputSchema': {
                'type': 'object',
                'properties': {},
                'required': []
            }
        },
        {
            'name': 'federalrunner_get_wizard_info',
            'description': (
                'Get detailed information about a specific wizard including its User Data Schema (THE CONTRACT). '
                'This returns the JSON Schema that defines what data you need to collect from the user. '
                'YOU must read this schema to understand field names, types, validation rules, and required fields. '
                'The schema tells you EXACTLY what user_data structure to build for execution. '
                'ALWAYS call this before executing a wizard to know what data to collect.'
            ),
            'inputSchema': {
                'type': 'object',
                'properties': {
                    'wizard_id': {
                        'type': 'string',
                        'description': 'Wizard identifier from federalrunner_list_wizards (e.g., "fsa-estimator")'
                    }
                },
                'required': ['wizard_id']
            }
        },
        {
            'name': 'federalrunner_execute_wizard',
            'description': (
                'Execute a federal form wizard with validated user data. '
                'This is an ATOMIC, MECHANICAL tool - it validates data against the schema, '
                'launches a headless browser, fills all form fields sequentially, and extracts results. '
                'YOU must first call federalrunner_get_wizard_info to get the schema, then collect '
                'ALL required data from the user by reading the schema properties, and finally call this tool. '
                'The user_data keys must match the property names from the schema (field_id). '
                'Returns execution results with screenshots showing each page filled. '
                'If validation fails, you will receive detailed error messages about which fields are missing/invalid.'
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
                            'User data matching the wizard\'s User Data Schema retrieved from federalrunner_get_wizard_info. '
                            'Property names must match schema field_ids exactly. '
                            'Values must conform to schema types and validation patterns. '
                            'All required fields from the schema must be present. '
                            'YOU are responsible for collecting this data from the user by reading the schema.'
                        ),
                        'additionalProperties': True
                    }
                },
                'required': ['wizard_id', 'user_data']
            }
        }
    ]


async def execute_tool(tool_name: str, arguments: Dict, scopes: list) -> Dict:
    """
    Execute the specified FederalRunner tool with given arguments.

    Validates scopes and delegates to execution_tools module.

    Args:
        tool_name: Name of the tool to execute
        arguments: Tool arguments
        scopes: OAuth scopes from token

    Returns:
        Dict containing 'content' with tool results

    Raises:
        HTTPException: If scope validation fails
    """
    logger.info(f"Executing tool: {tool_name}")
    logger.debug(f"Arguments: {arguments}")

    try:
        if tool_name == 'federalrunner_list_wizards':
            logger.info("Tool: federalrunner_list_wizards - Listing available wizards")
            # Requires federalrunner:read scope
            require_scope('federalrunner:read', scopes)

            result = await federalrunner_list_wizards()
            logger.info(f"Listed {result.get('count', 0)} wizards")

            return {
                'content': [
                    {
                        'type': 'text',
                        'text': json.dumps(result, indent=2)
                    }
                ]
            }

        elif tool_name == 'federalrunner_get_wizard_info':
            wizard_id = arguments.get('wizard_id')
            logger.info(f"Tool: federalrunner_get_wizard_info - Wizard: {wizard_id}")

            # Requires federalrunner:read scope
            require_scope('federalrunner:read', scopes)

            result = await federalrunner_get_wizard_info(wizard_id)
            logger.info(f"Retrieved wizard info: {result.get('name', 'Unknown')}")

            return {
                'content': [
                    {
                        'type': 'text',
                        'text': json.dumps(result, indent=2)
                    }
                ]
            }

        elif tool_name == 'federalrunner_execute_wizard':
            wizard_id = arguments.get('wizard_id')
            user_data = arguments.get('user_data', {})
            logger.info(f"Tool: federalrunner_execute_wizard - Wizard: {wizard_id}")
            logger.debug(f"User data fields: {list(user_data.keys())}")

            # Requires federalrunner:execute scope
            require_scope('federalrunner:execute', scopes)

            result = await federalrunner_execute_wizard(wizard_id, user_data)

            if result.get('success'):
                logger.info(f"Wizard execution successful: {wizard_id}")
            else:
                logger.error(f"Wizard execution failed: {result.get('error')}")

            # Build response content
            content = []

            # Include screenshots if available
            screenshots = result.get('screenshots', [])
            for i, screenshot_base64 in enumerate(screenshots):
                content.append({
                    'type': 'image',
                    'data': screenshot_base64,
                    'mimeType': 'image/jpeg'
                })

            # Add text results (without base64 data to avoid duplication)
            text_result = {
                k: v for k, v in result.items()
                if k != 'screenshots'
            }

            content.append({
                'type': 'text',
                'text': json.dumps(text_result, indent=2)
            })

            return {
                'content': content
            }

        else:
            return {
                'content': [
                    {
                        'type': 'text',
                        'text': json.dumps({
                            'success': False,
                            'error': f'Unknown tool: {tool_name}'
                        })
                    }
                ]
            }

    except HTTPException:
        # Re-raise scope validation errors
        raise

    except Exception as e:
        logger.error(f"Error executing tool {tool_name}: {e}")
        return {
            'content': [
                {
                    'type': 'text',
                    'text': json.dumps({
                        'success': False,
                        'error': str(e),
                        'error_type': type(e).__name__
                    })
                }
            ]
        }


# For local development/testing
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=config.port,
        reload=True
    )
