# Claude MCP OAuth and Transport Troubleshooting Guide

## The Root Cause of Your Issue

Your exact problem—OAuth succeeds, "Configure" button appears, but session terminates immediately after Claude sends GET / with Accept: text/event-stream and receives 501—is **caused by returning the wrong HTTP status code**. Claude interprets your 501 Not Implemented response as "this server is fundamentally broken" rather than "this server doesn't support SSE". The fix is straightforward: **return 405 Method Not Allowed instead of 501**.

---

## 1. The "Configure button visible but not connected" state

### What This State Means

The "Configure" button becomes visible when Claude has discovered your MCP server but hasn't yet established a working connection. This intermediate state occurs when:

**OAuth configuration discovered but not completed**
- Claude successfully fetched `/.well-known/oauth-authorization-server`
- User hasn't clicked "Configure" yet, or OAuth flow failed

**OAuth completed but session initialization failed**
- Access token obtained successfully
- Initialize request failed or timed out
- Transport negotiation failed

**Implicit connection vs. explicit connection**
- "Configure" button visible = Server discovered, OAuth endpoints found
- "Connected" status = Full handshake completed, tools available

### Common Root Causes

**Missing or malformed OAuth metadata endpoints** - Claude expects both `/.well-known/oauth-authorization-server` (required) and optionally `/.well-known/oauth-protected-resource`. If these return 404 or invalid JSON, the connection stalls.

**Dynamic Client Registration (DCR) failures** - Your server's `/oauth/register` endpoint must accept Claude's registration request with `client_name: "claudeai"`, `token_endpoint_auth_method: "none"`, and `redirect_uris: ["https://claude.ai/api/mcp/auth_callback"]`. Return a valid client_id in the response.

**Redirect URI mismatches** - The most common issue. Claude.ai uses `https://claude.ai/api/mcp/auth_callback` (and soon `https://claude.com/api/mcp/auth_callback`). Claude Desktop/Code uses dynamic localhost ports like `http://localhost:64236/callback`. Both must be registered in your OAuth provider.

**Token endpoint errors** - PKCE verification failures (Claude always uses S256), missing required token response fields (`access_token`, `token_type: "Bearer"`, `expires_in`), or incorrect token format.

**Transport negotiation failure** - This is your specific issue. Claude attempts to detect transport type, and incorrect HTTP status codes cause it to give up.

### Resolution Steps

Ensure your OAuth metadata endpoint returns:
```json
{
  "issuer": "https://your-server.com",
  "authorization_endpoint": "https://your-server.com/authorize",
  "token_endpoint": "https://your-server.com/token",
  "registration_endpoint": "https://your-server.com/register",
  "code_challenge_methods_supported": ["S256"],
  "token_endpoint_auth_methods_supported": ["none"],
  "grant_types_supported": ["authorization_code", "refresh_token"]
}
```

Register both current and future callback URLs:
- `https://claude.ai/api/mcp/auth_callback`
- `https://claude.com/api/mcp/auth_callback`

Token response must include all required fields:
```json
{
  "access_token": "eyJhbGci...",
  "token_type": "Bearer",
  "expires_in": 3600,
  "refresh_token": "tGzv3JOkF0...",
  "scope": "read write"
}
```

---

## 2. Dynamic Client Registration (DCR) Requirements

### DCR Registration Flow

Claude performs Dynamic Client Registration per RFC 7591 during the OAuth setup:

**Claude's DCR request to your /oauth/register endpoint:**
```json
{
  "client_name": "claudeai",
  "grant_types": ["authorization_code", "refresh_token"],
  "response_types": ["code"],
  "token_endpoint_auth_method": "none",
  "scope": "claudeai",
  "redirect_uris": ["https://claude.ai/api/mcp/auth_callback"]
}
```

**Your server must respond with:**
```json
{
  "client_id": "98f974d2-5ab1-467d-b043-64edbb2a840b",
  "client_name": "claudeai",
  "grant_types": ["authorization_code", "refresh_token"],
  "response_types": ["code"],
  "token_endpoint_auth_method": "none",
  "scope": "claudeai",
  "redirect_uris": ["https://claude.ai/api/mcp/auth_callback"]
}
```

### Critical DCR Requirements

**Public client handling** - `token_endpoint_auth_method: "none"` means Claude is a public client that cannot securely store secrets. Your token endpoint must not require client authentication for these registrations.

**PKCE is mandatory** - All authorization requests include `code_challenge` and `code_challenge_method: "S256"`. Your token endpoint must verify the `code_verifier` matches the original challenge.

**Unique client_id generation** - Generate a UUID or unique identifier for each registration and store it. Claude will use this client_id in all subsequent OAuth flows.

**Registration endpoint advertisement** - The `registration_endpoint` field in your OAuth metadata is required for DCR support.

### OAuth Provider Compatibility

**Providers that support DCR:**
- ✅ Auth0 (must enable "OIDC Dynamic Application Registration" in Advanced Settings)
- ✅ Stytch Connected Apps
- ✅ WorkOS
- ✅ Descope

**Providers that DO NOT support DCR:**
- ❌ Google OAuth
- ❌ GitHub OAuth
- ❌ Microsoft Azure AD/Entra ID
- ❌ Most enterprise identity providers

**Workaround for non-DCR providers**: As of July 2025, Claude Desktop allows manual entry of client_id and client_secret for servers that don't support DCR. Alternatively, implement a proxy that handles DCR and translates to your existing OAuth provider.

---

## 3. Redirect URI Pattern and Requirements

### Claude's OAuth Callback URLs

**Claude.ai (web):** `https://claude.ai/api/mcp/auth_callback`  
**Future URL:** `https://claude.com/api/mcp/auth_callback`  
**Claude Code CLI:** Dynamic localhost ports like `http://localhost:64236/callback`, `http://localhost:54212/callback`, etc.  
**MCP Inspector:** `http://localhost:6274/oauth/callback`

### Critical Configuration

**Exact matching required** - OAuth providers validate redirect URIs with exact string matching. `https://claude.ai/api/mcp/auth_callback` is different from `https://claude.ai/api/mcp/auth_callback/`.

**Register all variants** - Your OAuth provider configuration must include:
```
https://claude.ai/api/mcp/auth_callback
https://claude.com/api/mcp/auth_callback
http://localhost:6274/oauth/callback (for testing with MCP Inspector)
```

**Claude Code challenge** - Claude Code uses random ports, making it impossible to pre-register specific localhost URIs. For Claude Code support, either:
- Allow wildcard localhost redirects (if your provider supports it)
- Use a different OAuth provider that supports dynamic registration
- Implement your own proxy/wrapper

### Common Redirect URI Errors

**"Redirect URI not registered for client"** - Most commonly reported issue. Occurs when:
- Claude.ai skips DCR registration (known bug in web client)
- Provider doesn't have the exact URI registered
- URI includes trailing slash or query parameters that don't match

**Claude.ai vs Claude Desktop behavior difference** - The web client (claude.ai) has been observed skipping the DCR registration step in some cases, causing it to use an unregistered client_id. Claude Desktop and Claude Code properly perform DCR. This appears to be a client-side bug still being resolved.

---

## 4. Session Termination After OAuth/Initialization Handshake

### The Complete MCP Initialization Handshake

Your session termination issue stems from incomplete handshake handling. The MCP protocol requires **three steps**, not two:

**Step 1: Client → Server - initialize request**
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "initialize",
  "params": {
    "protocolVersion": "2025-03-26",
    "capabilities": {"roots": {"listChanged": true}},
    "clientInfo": {"name": "Claude", "version": "1.0"}
  }
}
```

**Step 2: Server → Client - initialize response**
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "protocolVersion": "2024-11-05",
    "capabilities": {"tools": {}, "resources": {}},
    "serverInfo": {"name": "MyServer", "version": "1.0.0"}
  }
}
```
**Critical:** Include `Mcp-Session-Id` header in response

**Step 3: Client → Server - notifications/initialized notification**
```json
{
  "jsonrpc": "2.0",
  "method": "notifications/initialized"
}
```
**Note:** This has no `id` field (it's a notification)

### Critical Implementation Requirements

**Handle notifications/initialized** - Many servers forget step 3. This notification has `id: null` and expects a 202 Accepted response with no body:

```javascript
if (method === 'notifications/initialized') {
  return res.status(202).end();  // No JSON response
}
```

**Session ID management** - The server generates a session ID during initialize and returns it in the `Mcp-Session-Id` header. All subsequent client requests MUST include this header, and the server must validate it:

```javascript
const sessionId = req.headers['mcp-session-id'];
if (!sessionId || !transports[sessionId]) {
  return res.status(400).json({
    jsonrpc: '2.0',
    error: {code: -32003, message: 'Invalid session ID'},
    id: body?.id || null
  });
}
```

**Authentication timing** - Authenticate after initialize but before tool operations. The initialize request itself typically doesn't require authentication, allowing the server to return its capabilities before validating credentials.

### Known Session Termination Issues

**OpenAI/GitHub MCP server issue** - First interaction works, but subsequent tool calls fail with "Session terminated" error. This is a widespread issue affecting OpenAI's Responses API with remote MCP servers. Workaround: Set `stateless_http=True` in server configuration.

**VS Code not sending new initialize on 404** - VS Code doesn't comply with the spec requirement to send a new initialize request when receiving HTTP 404 for an invalid session ID. Instead it logs an error and gives up.

**Continue client sends requests out of order** - The Continue VS Code extension sends GET for initialization instead of POST, and doesn't include the Mcp-Session-Id header.

---

## 5. Empty Capabilities and Transport Types

### Understanding the Separation of Concerns

**Critical concept:** Capabilities and transport types operate at different protocol layers and are **completely independent**.

**Capabilities layer (application layer)** - Defines what MCP primitives the server supports:
```json
{
  "capabilities": {
    "tools": {},          // Server supports tools primitive
    "resources": {},      // Server supports resources primitive
    "prompts": {}         // Server supports prompts primitive
  }
}
```

**Transport layer (communication layer)** - Defines how messages are transmitted:
- stdio (stdin/stdout)
- Legacy HTTP+SSE (2024-11-05 spec)
- Streamable HTTP (2025-03-26 spec) - supports POST-only OR POST+GET

### Empty Capabilities Are Normal

Empty capabilities like `{"tools": {}}` mean:
- The server **supports** the tools primitive
- The server **does not** support optional sub-features like `"listChanged": true`
- This is **completely valid** and extremely common

Empty capabilities do **NOT** indicate:
- Transport type preference
- POST-only vs SSE support
- Whether the server uses JSON or streaming responses

A server with `{"tools": {}}` can use any transport type. The transport negotiation happens separately.

### How Transport Selection Actually Works

Transport type is determined by:
1. **Client capabilities** - What transports the client supports
2. **Server endpoint implementation** - Which HTTP methods the server responds to
3. **Transport detection algorithm** - How the client discovers server capabilities
4. **Not by the capabilities object** in the initialize response

---

## 6. Why Claude Attempts GET Requests Despite POST-Only Capabilities

### The Backwards Compatibility Detection Algorithm

This is the **exact cause of your issue**. Claude implements a transport detection algorithm to support both legacy (2024-11-05) and modern (2025-03-26) MCP servers:

**Step 1: Try modern Streamable HTTP (POST)**
```
POST /mcp
Headers: Accept: application/json, text/event-stream
Body: initialize request

Success (200/202) → Use Streamable HTTP
Failure (4xx) → Fall back to step 2
```

**Step 2: Try legacy HTTP+SSE (GET)**
```
GET /mcp
Headers: Accept: text/event-stream

Success (200) → Expect SSE stream with "endpoint" event
Failure (405) → Back to Streamable HTTP (POST-only mode)
Failure (501) → Server error, terminate session ← YOUR ISSUE
```

### Why Your 501 Response Causes Termination

When Claude receives **501 Not Implemented**, it interprets this as "the server doesn't understand GET at all, something is fundamentally wrong." According to HTTP specifications:

**501 Not Implemented** - Server does not recognize the method and cannot support it for any resource. This is a permanent error condition.

**405 Method Not Allowed** - Server recognizes the method but the specific resource doesn't allow it. The server should include an `Allow` header showing which methods are supported.

Your server is returning 501, telling Claude "I don't understand what a GET request is", when you should be returning 405, telling Claude "I understand GET but this endpoint only accepts POST".

### The Correct Implementation

**For POST-only Streamable HTTP servers:**

```javascript
app.get('/mcp', (req, res) => {
  res.status(405)
    .set('Allow', 'POST')
    .json({
      jsonrpc: '2.0',
      error: {
        code: -32000,
        message: 'Method Not Allowed. Use POST for Streamable HTTP transport.'
      },
      id: null
    });
});
```

**This tells Claude:** "I'm a POST-only Streamable HTTP server, don't try SSE."

**Result:** Claude receives 405, understands the server is POST-only, and proceeds with the connection instead of terminating.

### Additional Transport Negotiation Best Practices

**Accept header validation** - Your POST endpoint should validate that clients send both content types:

```javascript
const accept = req.headers['accept'] || '';
if (!accept.includes('application/json') || !accept.includes('text/event-stream')) {
  return res.status(406).json({
    jsonrpc: '2.0',
    error: {
      code: -32600,
      message: 'Not Acceptable: Client must accept both application/json and text/event-stream'
    },
    id: body?.id || null
  });
}
```

**Transport configuration** - When creating your StreamableHTTPServerTransport:

```javascript
const transport = new StreamableHTTPServerTransport({
  enableJsonResponse: true,      // Support JSON responses
  eventSourceEnabled: false,     // Disable GET/SSE support
});
```

---

## 7. Common OAuth Provider Pitfalls

### Auth0 Configuration Issues

Auth0 requires specific configuration to work with MCP:

**Enable Dynamic Client Registration**
- Dashboard → Applications → SSO Integrations
- Enable "OIDC Dynamic Application Registration"
- This is disabled by default for security

**Configure token format**
- Set Default Audience in API settings
- Without this, Auth0 issues opaque tokens instead of JWTs
- MCP servers expect JWTs for validation

**Promote connections to domain-level**
- Required for third-party apps like Claude
- Use Management API with `update:connections` and `read:connections` scopes
- Connections created in specific applications aren't accessible domain-wide

**Allow callback URLs**
- Add `https://claude.ai` and `https://claude.com` to allowed callback URLs
- Add your application's origin for CORS

### Azure AD/Entra ID Issues

**No DCR support** - Azure doesn't support Dynamic Client Registration at all. You must:
- Pre-register an application manually in Azure Portal
- Implement a proxy/wrapper that fakes DCR registration
- Or use Claude Desktop's manual client_id/secret entry (July 2025+)

**Path differences** - Azure requires `/oauth2/` in authorization paths:
- Wrong: `https://login.microsoftonline.com/{tenant}/v2.0/authorize`
- Correct: `https://login.microsoftonline.com/{tenant}/oauth2/v2.0/authorize`

**Scope validation** - Azure enforces strict scope validation and rejects requests without proper scope format: `api://{app-id}/scope-name`

### Google OAuth Issues

**No DCR support** - Google requires manual client registration in Cloud Console.

**Fixed redirect URIs only** - Cannot accommodate Claude Code's dynamic ports.

**Workaround required** - Implement a proxy server that handles DCR and maps to your pre-registered Google OAuth client.

### GitHub MCP OAuth Issues

**Works with some clients, not others** - GitHub's official MCP server works with VS Code but fails with Claude apps. This is a known compatibility issue (GitHub issue #549).

**Discovery failures** - Some clients report "401 error received for SSE server 'github' without OAuth configuration" when failing to discover GitHub's OAuth endpoints.

---

## 8. Token Response Format Requirements

### Required Token Response Fields

Your token endpoint must return all of these fields:

```json
{
  "access_token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "Bearer",
  "expires_in": 3600,
  "refresh_token": "tGzv3JOkF0XG5Qx2TlKWIA",
  "scope": "tools:read tools:write"
}
```

### Field Requirements

**access_token** - Can be JWT or opaque token. If JWT, must include:
- `iss` (issuer) - Your authorization server URL
- `aud` (audience) - Your MCP server URL
- `exp` (expiration) - Unix timestamp
- `sub` (subject) - User identifier

**token_type** - Must be exactly `"Bearer"` (case-sensitive)

**expires_in** - Token lifetime in seconds (integer, not string)

**refresh_token** - Required for long-lived sessions. Should be rotated on each use per OAuth 2.1 best practices.

**scope** - Space-separated list of granted scopes. May differ from requested scopes.

### What Causes Claude to Get Stuck on "Configure"

**Missing required fields** - If any of the required fields above are missing or misspelled (e.g., `expires_in` as string `"3600"` instead of integer `3600`), Claude may fail silently.

**Invalid token_type** - Must be `"Bearer"`, not `"bearer"` or `"JWT"`.

**Opaque tokens without validation endpoint** - If you issue opaque tokens, your MCP server needs a way to validate them. Without validation, authenticated requests fail.

**Token not bound to MCP server** - For third-party OAuth (Section 2.9.2 of MCP auth spec), your MCP server must generate its own token bound to the third-party session. Simply forwarding the third-party token doesn't work.

**PKCE verification failures** - Your token endpoint must verify the `code_verifier` matches the original `code_challenge`:

```javascript
const hash = crypto.createHash('sha256').update(codeVerifier).digest('base64url');
if (hash !== storedCodeChallenge) {
  return res.status(400).json({
    error: 'invalid_grant',
    error_description: 'PKCE verification failed'
  });
}
```

### Token Validation Requirements

Your MCP server must validate access tokens on every request:

```javascript
async function validateToken(token) {
  // For JWTs
  const decoded = jwt.verify(token, publicKey, {
    algorithms: ['RS256'],
    issuer: 'https://auth.example.com',
    audience: 'https://mcp.example.com'
  });
  
  // Check expiration
  if (decoded.exp < Date.now() / 1000) {
    throw new Error('Token expired');
  }
  
  return decoded;
}
```

**Invalid tokens must receive HTTP 401** with `WWW-Authenticate: Bearer` header pointing to your OAuth metadata.

---

## 9. Known Issues with SSE Connections and Session Termination

### Widespread SSE Connection Attempts

Multiple clients have been observed attempting SSE connections when they shouldn't:

**Claude Desktop/Code** - Attempts GET with `Accept: text/event-stream` after POST failures, even for POST-only servers.

**VS Code Copilot** - Sends GET requests for SSE but doesn't properly handle 405 responses.

**Cursor** - Connects successfully showing yellow dot but never sends tools/list request after receiving mcp/hello over SSE.

**OpenAI Responses API** - First interaction works but subsequent tool calls fail with "Session terminated" error.

### Root Cause Analysis

**Transport confusion** - Clients implementing both legacy SSE (2024-11-05) and modern Streamable HTTP (2025-03-26) have fragile detection logic that breaks when servers return unexpected status codes.

**Session state loss** - Some clients don't persist session IDs between tool calls, causing each new request to appear as a new session.

**Race conditions** - Creating multiple transports for the same session when handling rapid requests leads to session cleanup before initialization completes.

**Missing notifications/initialized** - Claude Code was found to skip this step entirely in some versions, causing properly-implemented servers to reject subsequent requests as "not initialized".

### Known Bugs in MCP Clients

**Claude.ai web skips DCR** - The web client doesn't perform Dynamic Client Registration, leading to "Client ID not found" errors. Claude Desktop and Claude Code work correctly.

**VS Code doesn't retry on session 404** - Per the MCP spec, clients should send a new initialize request when receiving 404 for an invalid session. VS Code logs an error and gives up instead.

**Continue sends GET for initialization** - The Continue extension sends GET instead of POST for the initialize request, violating the Streamable HTTP transport spec.

**OpenAI stateless issues** - OpenAI clients don't maintain session state between tool calls by default. Workaround: Set `stateless_http=True` on server or use `previous_response_id` to maintain conversation state.

---

## 10. Best Practices for POST-Only MCP Servers with OAuth

### Complete Production-Ready Implementation Pattern

**1. Return correct HTTP status codes**

```javascript
// POST-only endpoint
app.get('/mcp', (req, res) => {
  res.status(405).set('Allow', 'POST').json({
    jsonrpc: '2.0',
    error: {code: -32000, message: 'Method Not Allowed'},
    id: null
  });
});

app.post('/mcp', async (req, res) => {
  // Handle requests
});
```

**2. Implement complete three-step handshake**

```javascript
if (method === 'initialize') {
  const sessionId = uuidv4();
  res.setHeader('Mcp-Session-Id', sessionId);
  // ... create transport and respond
}

if (method === 'notifications/initialized') {
  return res.status(202).end();  // No JSON body
}
```

**3. Validate Accept headers**

```javascript
const accept = req.headers['accept'] || '';
if (!accept.includes('application/json') || !accept.includes('text/event-stream')) {
  return res.status(406).json({...});
}
```

**4. Implement proper session management**

```javascript
const transports = {};

// Store during initialize
transports[sessionId] = transport;

// Retrieve for subsequent requests
const sessionId = req.headers['mcp-session-id'];
const transport = transports[sessionId];
if (!transport) {
  return res.status(400).json({
    jsonrpc: '2.0',
    error: {code: -32003, message: 'Invalid session ID'},
    id: body?.id || null
  });
}
```

**5. Authenticate after initialize**

```javascript
if (method === 'initialize') {
  // No auth required
} else if (method === 'notifications/initialized') {
  // No auth required
} else {
  // All other methods require authentication
  const authResult = await authenticateToken(req, res);
  if (!authResult.success) {
    return authResult.response;
  }
}
```

**6. Provide OAuth discovery endpoints**

```javascript
app.get('/.well-known/oauth-authorization-server', (req, res) => {
  res.json({
    issuer: baseUrl,
    authorization_endpoint: `${baseUrl}/authorize`,
    token_endpoint: `${baseUrl}/token`,
    registration_endpoint: `${baseUrl}/register`,
    code_challenge_methods_supported: ['S256'],
    token_endpoint_auth_methods_supported: ['none'],
    grant_types_supported: ['authorization_code', 'refresh_token']
  });
});
```

**7. Handle CORS properly**

```javascript
app.use((req, res, next) => {
  res.header('Access-Control-Allow-Origin', '*');
  res.header('Access-Control-Allow-Methods', 'POST, DELETE, OPTIONS');
  res.header('Access-Control-Allow-Headers', 'Content-Type, Accept, Authorization, Mcp-Session-Id');
  res.header('Access-Control-Expose-Headers', 'Mcp-Session-Id, WWW-Authenticate');
  
  if (req.method === 'OPTIONS') {
    return res.status(200).end();
  }
  next();
});
```

### Testing Checklist

✅ GET /mcp returns 405 with Allow: POST header  
✅ POST /mcp without Accept header returns 406  
✅ POST /mcp with initialize returns Mcp-Session-Id header  
✅ POST /mcp with notifications/initialized returns 202  
✅ POST /mcp with invalid session ID returns 400  
✅ POST /mcp without auth token returns 401 with WWW-Authenticate  
✅ OAuth metadata endpoints return valid JSON  
✅ DCR registration creates and returns client_id  
✅ Token endpoint validates PKCE and returns all required fields  
✅ Session persists across multiple tool calls  

### Common Implementation Mistakes to Avoid

❌ Returning 501 instead of 405 for GET requests  
❌ Forgetting to handle notifications/initialized  
❌ Not setting Mcp-Session-Id header in responses  
❌ Requiring authentication for initialize request  
❌ Validating Accept header too strictly (exact string match)  
❌ Creating new transport on every request instead of reusing by session  
❌ Not implementing refresh token support  
❌ Using client authentication for public clients  

---

## Step-by-Step Fix for Your Specific Issue

Based on your exact symptoms, here's what to change:

### 1. Change Your GET Handler (PRIMARY FIX)

**Replace this:**
```javascript
app.get('/', (req, res) => {
  res.status(501).send('Not Implemented');
});
```

**With this:**
```javascript
app.get('/', (req, res) => {
  res.status(405)
    .set('Allow', 'POST')
    .json({
      jsonrpc: '2.0',
      error: {
        code: -32000,
        message: 'Method Not Allowed. Use POST for Streamable HTTP transport.'
      },
      id: null
    });
});
```

### 2. Ensure Initialize Returns Session ID

```javascript
if (body.method === 'initialize') {
  const sessionId = crypto.randomUUID();
  res.setHeader('Mcp-Session-Id', sessionId);
  // Store transport with this session ID
}
```

### 3. Add notifications/initialized Handler

```javascript
if (body.method === 'notifications/initialized') {
  return res.status(202).end();  // No JSON response
}
```

### 4. Test the Full Flow

```bash
# Should return 405, not 501
curl -X GET http://localhost:3000/mcp -H "Accept: text/event-stream"

# Should return 200 with Mcp-Session-Id header
curl -X POST http://localhost:3000/mcp \
  -H "Accept: application/json, text/event-stream" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{}}}'
```

This single change from 501 to 405 should resolve your immediate session termination issue. Claude will receive the 405, understand your server is POST-only, and continue with the connection instead of terminating.

---

## Additional Resources

**Official Documentation:**
- MCP Authorization Spec: https://modelcontextprotocol.io/specification/2025-06-18/basic/authorization
- Anthropic MCP Guide: https://support.claude.com/en/articles/11503834-building-custom-connectors-via-remote-mcp-servers

**Implementation Examples:**
- FastMCP with OAuth: https://github.com/jlowin/fastmcp
- Remote MCP with Auth0: https://github.com/coleam00/remote-mcp-server-with-auth
- Stytch MCP Example: https://stytch.com/blog/oauth-for-mcp-explained-with-a-real-world-example

**Community Tools:**
- MCP Inspector: `npx @modelcontextprotocol/inspector` (for testing)
- mcp-remote: https://github.com/geelen/mcp-remote (OAuth proxy for clients without native support)
- mcp-proxy: https://github.com/sparfenyuk/mcp-proxy (transport bridge)

**Troubleshooting:**
- GitHub modelcontextprotocol/modelcontextprotocol (specifications and discussions)
- GitHub anthropics/claude-code (client-specific issues)
- Auth0 MCP Guide: https://auth0.com/ai/docs/mcp/auth-for-mcp