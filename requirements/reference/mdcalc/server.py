"""
FastAPI server for MDCalc MCP with OAuth 2.1 authentication.

This server implements the Model Context Protocol (MCP) specification 2025-06-18
for providing MDCalc medical calculator automation to AI assistants like Claude.

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
    1. HEAD / → 200 with MCP-Protocol-Version header
    2. GET /.well-known/oauth-protected-resource → OAuth config
    3. POST / initialize → Session created (no auth required)
    4. POST / notifications/initialized → 202 Accepted (session validation only)
    5. GET / → 405 Method Not Allowed (transport detection)
    6. User authenticates via Auth0 OAuth flow
    7. POST / tools/list → 200 with tools (OAuth + session validated)
    8. POST / tools/call → Calculator execution (OAuth + session validated)

For deployment instructions, see docs/deployment/DEPLOYMENT_GUIDE.md
For troubleshooting, see docs/deployment/LESSONS_LEARNED.md
"""

import json
from typing import Dict, Any, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse, Response
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .auth import verify_token_manual, get_token_scopes, require_scope
from .mdcalc_client import MDCalcClient
from .logging_config import get_logger

# Setup logger for this module
logger = get_logger(__name__)

# Global MDCalc client instance
mdcalc_client: Optional[MDCalcClient] = None

# Session management
sessions: Dict[str, Dict[str, Any]] = {}  # session_id -> session data
session_initialized: Dict[str, bool] = {}  # session_id -> initialization status


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for FastAPI.
    Initialize and cleanup resources.
    """
    global mdcalc_client

    # Startup
    logger.info("="*60)
    logger.info("MDCalc MCP Server Starting")
    logger.info("="*60)
    logger.info(f"Environment: {'Cloud Run' if settings.MCP_SERVER_URL.startswith('https') else 'Local Development'}")
    logger.info(f"Auth0 Domain: {settings.AUTH0_DOMAIN}")
    logger.info(f"API Audience: {settings.AUTH0_API_AUDIENCE}")
    logger.info(f"Server URL: {settings.MCP_SERVER_URL}")
    logger.info(f"Port: {settings.PORT}")

    logger.info("Initializing MDCalc client in headless mode...")
    mdcalc_client = MDCalcClient()

    try:
        await mdcalc_client.initialize(headless=True, use_auth=True)
        logger.info("✅ MDCalc client initialized successfully")
        logger.info("✅ MDCalc MCP Server ready to accept requests")
    except Exception as e:
        logger.error(f"❌ Failed to initialize MDCalc client: {e}")
        raise

    yield

    # Shutdown
    logger.info("="*60)
    logger.info("MDCalc MCP Server Shutting Down")
    logger.info("="*60)
    if mdcalc_client:
        logger.info("Cleaning up MDCalc client...")
        await mdcalc_client.cleanup()
        logger.info("✅ MDCalc client cleaned up")
    logger.info("✅ MDCalc MCP Server stopped")


# Create FastAPI app
app = FastAPI(
    title="MDCalc MCP Server",
    description="Remote MCP server for MDCalc automation with OAuth 2.1",
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
    logger.info(f"📨 Incoming request: {request.method} {request.url.path}")

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
    logger.info(f"📤 Response: {response.status_code}")

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
        "service": "mdcalc-mcp-server",
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
    logger.debug(f"Returning Auth0 domain: {settings.AUTH0_DOMAIN}")

    return {
        "resource": settings.MCP_SERVER_URL,
        "authorization_servers": [f"https://{settings.AUTH0_DOMAIN}"],
        "bearer_methods_supported": ["header"],
        "scopes_supported": ["mdcalc:read", "mdcalc:calculate"]
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
                        'name': 'mdcalc-mcp-server',
                        'title': 'MDCalc Medical Calculator Automation',
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
            logger.info(f"✅ Session {session_id} is now FULLY INITIALIZED")

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
    Return available MDCalc MCP tools.

    These are atomic, mechanical operations. Claude handles ALL intelligence,
    clinical interpretation, and data mapping. The tools simply navigate,
    screenshot, click, and extract.
    """
    return [
        {
            'name': 'mdcalc_list_all',
            'description': (
                'Get the complete catalog of all 825 MDCalc calculators in an optimized format (~31K tokens). '
                'Returns compact list with just ID, name, and medical category for each calculator. '
                'Use for comprehensive assessments where you need to review all available options by specialty. '
                'URLs can be constructed as: https://www.mdcalc.com/calc/{id}'
            ),
            'inputSchema': {
                'type': 'object',
                'properties': {},
                'required': []
            }
        },
        {
            'name': 'mdcalc_search',
            'description': (
                'Search MDCalc using their sophisticated web search that understands clinical relationships. '
                'Returns semantically relevant calculators, not just keyword matches. '
                'Use for targeted queries when you know what you are looking for. '
                'Example queries: "chest pain" (finds HEART, TIMI), "afib" (finds CHA2DS2-VASc), "sepsis" (finds SOFA).'
            ),
            'inputSchema': {
                'type': 'object',
                'properties': {
                    'query': {
                        'type': 'string',
                        'description': 'Search term - can be condition (e.g., "chest pain"), symptom (e.g., "dyspnea"), body system (e.g., "cardiac"), or calculator name (e.g., "HEART Score")'
                    },
                    'limit': {
                        'type': 'integer',
                        'description': 'Maximum number of results to return (default: 10, max: 50)',
                        'default': 10,
                        'minimum': 1,
                        'maximum': 50
                    }
                },
                'required': ['query']
            }
        },
        {
            'name': 'mdcalc_get_calculator',
            'description': (
                'Get a screenshot and details of a specific MDCalc calculator. '
                'Returns a JPEG screenshot (23KB) of the calculator interface for visual understanding, '
                'plus metadata including title and URL. The screenshot shows all input fields, options, '
                'and current values. YOU must use vision to understand the calculator structure and '
                'map patient data to the appropriate buttons/inputs shown in the screenshot.'
            ),
            'inputSchema': {
                'type': 'object',
                'properties': {
                    'calculator_id': {
                        'type': 'string',
                        'description': (
                            'MDCalc calculator ID or slug. Can be numeric ID (e.g., "1752" for HEART Score) '
                            'or slug format (e.g., "heart-score", "cha2ds2-vasc", "curb-65"). '
                            'Get IDs from mdcalc_search or mdcalc_list_all results.'
                        )
                    }
                },
                'required': ['calculator_id']
            }
        },
        {
            'name': 'mdcalc_execute',
            'description': (
                'Execute a calculator by filling inputs and clicking buttons based on provided values. '
                'This is a MECHANICAL tool - it only clicks what you tell it. YOU must: '
                '1) First call mdcalc_get_calculator to SEE the calculator visually, '
                '2) Map patient data to the EXACT button text or input values shown, '
                '3) Pass the mapped values to this tool. '
                'Returns calculation results AND a result screenshot showing all inputs and results. '
                'ALWAYS examine the result screenshot to verify correct execution and see conditional fields.'
            ),
            'inputSchema': {
                'type': 'object',
                'properties': {
                    'calculator_id': {
                        'type': 'string',
                        'description': 'MDCalc calculator ID (e.g., "1752") or slug (e.g., "heart-score")'
                    },
                    'inputs': {
                        'type': 'object',
                        'description': (
                            'Field values mapped to calculator inputs. Keys should be field names '
                            '(e.g., "age", "history", "troponin"). Values must match EXACT button text '
                            'as shown in screenshot (e.g., "≥65", "Moderately suspicious", "≤1x normal limit"). '
                            'For numeric inputs, provide the numeric value. YOU are responsible for all mapping.'
                        ),
                        'additionalProperties': {
                            'type': 'string'
                        }
                    }
                },
                'required': ['calculator_id', 'inputs']
            }
        }
    ]


async def execute_tool(tool_name: str, arguments: Dict, scopes: list) -> Dict:
    """
    Execute the specified MDCalc tool with given arguments.

    Validates scopes and delegates to MDCalcClient.

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
        if tool_name == 'mdcalc_list_all':
            logger.info("Tool: mdcalc_list_all - Getting complete calculator catalog")
            # Requires mdcalc:read scope
            require_scope('mdcalc:read', scopes)

            calculators = await mdcalc_client.get_all_calculators()
            logger.info(f"Retrieved {len(calculators)} calculators")

            # Group by category
            by_category = {}
            for calc in calculators:
                category = calc.get('category', 'Other')
                if category not in by_category:
                    by_category[category] = []
                by_category[category].append(calc)

            logger.info(f"Grouped into {len(by_category)} categories")

            return {
                'content': [
                    {
                        'type': 'text',
                        'text': json.dumps({
                            'success': True,
                            'total_count': len(calculators),
                            'categories': list(by_category.keys()),
                            'calculators_by_category': by_category,
                            'all_calculators': calculators
                        }, indent=2)
                    }
                ]
            }

        elif tool_name == 'mdcalc_search':
            query = arguments.get('query', '')
            limit = arguments.get('limit', 10)
            logger.info(f"Tool: mdcalc_search - Query: '{query}', Limit: {limit}")

            # Requires mdcalc:read scope
            require_scope('mdcalc:read', scopes)

            results = await mdcalc_client.search_calculators(query, limit)
            logger.info(f"Search returned {len(results)} results")

            return {
                'content': [
                    {
                        'type': 'text',
                        'text': json.dumps({
                            'success': True,
                            'count': len(results),
                            'calculators': results
                        }, indent=2)
                    }
                ]
            }

        elif tool_name == 'mdcalc_get_calculator':
            calculator_id = arguments.get('calculator_id')
            logger.info(f"Tool: mdcalc_get_calculator - ID: {calculator_id}")

            # Requires mdcalc:read scope
            require_scope('mdcalc:read', scopes)

            logger.debug(f"Fetching calculator details and screenshot for {calculator_id}")
            details = await mdcalc_client.get_calculator_details(calculator_id)
            logger.info(f"Retrieved details for: {details.get('title', 'Unknown')}")

            # Build response with screenshot as image content
            content = []

            # Add the screenshot as an image if available
            if details.get('screenshot_base64'):
                content.append({
                    'type': 'image',
                    'data': details['screenshot_base64'],
                    'mimeType': 'image/jpeg'
                })

            # Add text details (without the base64 data)
            calculator_info = {
                'success': True,
                'title': details.get('title'),
                'url': details.get('url'),
                'fields_detected': len(details.get('fields', [])),
                'screenshot_included': bool(details.get('screenshot_base64'))
            }

            content.append({
                'type': 'text',
                'text': json.dumps(calculator_info, indent=2)
            })

            return {
                'content': content
            }

        elif tool_name == 'mdcalc_execute':
            calculator_id = arguments.get('calculator_id')
            inputs = arguments.get('inputs', {})
            logger.info(f"Tool: mdcalc_execute - ID: {calculator_id}")
            logger.debug(f"Inputs: {inputs}")

            # Requires mdcalc:calculate scope
            require_scope('mdcalc:calculate', scopes)

            logger.debug(f"Executing calculator {calculator_id} with {len(inputs)} inputs")
            result = await mdcalc_client.execute_calculator(calculator_id, inputs)
            logger.info(f"Calculation complete: {result.get('score', 'No score')}")

            # Parse the score from the result
            score_text = result.get('score', '')
            risk_text = result.get('risk', '')

            # Extract numeric score if present
            score_value = None
            if score_text and 'point' in score_text.lower():
                import re
                match = re.search(r'(\d+)\s*point', score_text.lower())
                if match:
                    score_value = int(match.group(1))

            # Clean up risk text
            if risk_text:
                import re
                # Extract the actual risk percentage if present
                risk_match = re.search(r'Risk.*?(\d+\.?\d*%)', risk_text)
                if risk_match:
                    risk_percentage = risk_match.group(1)
                else:
                    risk_percentage = None

                # Extract risk category
                if 'Low Score' in risk_text:
                    risk_category = 'Low'
                elif 'Moderate Score' in risk_text:
                    risk_category = 'Moderate'
                elif 'High Score' in risk_text:
                    risk_category = 'High'
                else:
                    risk_category = None
            else:
                risk_percentage = None
                risk_category = None

            # Build response content
            content = []

            # Include the result screenshot if available
            if result.get('result_screenshot_base64'):
                content.append({
                    'type': 'image',
                    'data': result['result_screenshot_base64'],
                    'mimeType': 'image/jpeg'
                })

            # Add text results (without the base64 data)
            text_result = {
                'success': result.get('success', False),
                'score': score_value,
                'score_text': score_text,
                'risk_category': risk_category,
                'risk_percentage': risk_percentage,
                'screenshot_included': bool(result.get('result_screenshot_base64')),
                'interpretation': result.get('interpretation'),
                'recommendations': result.get('recommendations')
            }

            # Only include full_result if no screenshot (to avoid duplication)
            if not result.get('result_screenshot_base64'):
                text_result['full_result'] = {
                    k: v for k, v in result.items()
                    if k != 'result_screenshot_base64'
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
                        'error': str(e)
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
        port=settings.PORT,
        reload=True
    )
