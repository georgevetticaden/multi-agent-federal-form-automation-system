# The Complete OAuth Handshake: Claude.ai ↔ Remote MCP Server ↔ Auth0

**Based on real logs from a working implementation**

After two days of debugging, here's the exact handshake flow that successfully connects Claude.ai to a remote MCP server with OAuth 2.1 authentication. This is one of the first documented working implementations.

---

## Phase 1: Discovery (The Reconnaissance)

**Timestamp: 18:39:12 UTC**

### Step 1.1: Protocol Check

```
HEAD / 
User-Agent: python-httpx/0.27.0
MCP-Protocol-Version: 2025-06-18

→ Response: 200 OK
   MCP-Protocol-Version: 2025-06-18
```

**What happened:**
- Claude.ai sent a HEAD request to check if the server supports MCP
- Note the user agent: `python-httpx` (Claude's discovery client)
- The server responded with matching protocol version

**Why this matters:**
- This is Claude's first contact with your server
- If this fails (404, timeout), Claude won't proceed
- The matching version confirms protocol compatibility

### Step 1.2: OAuth Discovery (RFC 9728)

```
GET /.well-known/oauth-protected-resource
User-Agent: python-httpx/0.27.0
MCP-Protocol-Version: 2025-06-18

→ Response: 200 OK
{
  "resource": "https://your-mcp-server.run.app",
  "authorization_servers": ["https://your-tenant.auth0.com"],
  "bearer_methods_supported": ["header"],
  "scopes_supported": ["mcp:read", "mcp:execute"]
}
```

**Server logs show:**
```
INFO - OAuth metadata requested (for DCR discovery)
DEBUG - Returning Auth0 domain: your-tenant.auth0.com
```

**What happened:**
- Claude fetched the OAuth configuration
- Discovered the authorization server (Auth0)
- Learned what scopes are available
- Prepared for Dynamic Client Registration (DCR)

**Critical insight:**
This is why the endpoint MUST return the correct Auth0 domain. If this is wrong, Claude can't find the authorization server and the flow stops here.

---

## Phase 2: User Authentication (The Missing Minutes)

**Timestamp: 18:39:12 → 18:41:11 (2 minute gap)**

Between these log entries, several things happened that we don't see in the MCP server logs:

### Step 2.1: Dynamic Client Registration (DCR)

Claude.ai contacted Auth0 directly:
```
POST https://your-tenant.auth0.com/oidc/register
{
  "client_name": "Claude MCP Client",
  "redirect_uris": ["https://claude.ai/oauth/callback"],
  "grant_types": ["authorization_code"],
  "response_types": ["code"],
  "token_endpoint_auth_method": "none"
}

→ Auth0 Response:
{
  "client_id": "auto-generated-client-id",
  "client_secret": null  // Public client
}
```

**What happened:**
- Claude registered itself as an OAuth client with Auth0
- Auth0 generated a client ID on the fly
- No client secret needed (PKCE will be used instead)

### Step 2.2: Authorization Request

Claude redirected the user's browser to:
```
https://your-tenant.auth0.com/authorize?
  client_id=auto-generated-client-id&
  redirect_uri=https://claude.ai/oauth/callback&
  response_type=code&
  scope=mcp:read%20mcp:execute&
  state=random-state&
  code_challenge=sha256-of-verifier&
  code_challenge_method=S256
```

### Step 2.3: User Interaction

The user saw:
1. Auth0 login page
2. Entered email/password
3. Saw consent screen showing requested scopes:
   - `mcp:read` - Read calculator information
   - `mcp:execute` - Calculate medical scores
4. Clicked "Agree"

### Step 2.4: Token Exchange

After user consent, Auth0 redirected back to Claude with authorization code:
```
https://claude.ai/oauth/callback?
  code=authorization-code&
  state=random-state
```

Claude then exchanged the code for tokens:
```
POST https://your-tenant.auth0.com/oauth/token
{
  "grant_type": "authorization_code",
  "code": "authorization-code",
  "redirect_uri": "https://claude.ai/oauth/callback",
  "client_id": "auto-generated-client-id",
  "code_verifier": "original-random-verifier"
}

→ Auth0 Response:
{
  "access_token": "eyJhbGciOiJkaXIiLCJlbmMi...",  // JWE token
  "token_type": "Bearer",
  "expires_in": 86400,
  "scope": "mcp:read mcp:execute"
}
```

**Critical insight:**
The token is a **JWE (JSON Web Encryption)**, not a JWT. This is why it has no `kid` field and requires validation via Auth0's userinfo endpoint instead of JWKS.

---

## Phase 3: MCP Handshake (The Connection)

**Timestamp: 18:41:11.561778Z**

### Step 3.1: Initialize (NO Authentication)

```
POST / 
User-Agent: Claude-User  ← Changed from python-httpx!
Authorization: Bearer eyJhbGciOiJkaXIiLCJlbmMi...
Content-Type: application/json

{
  "capabilities": {},
  "name": "claude-ai",
  "version": "0.1.0"
}
```

**Server logs:**
```
INFO - MCP request: method=initialize, id=0
INFO - Created MCP session: ed0fee05-fdbf-406f-8aee-b451fd29ee46 (fully initialized)
```

**Response:**
```
200 OK
MCP-Session-ID: ed0fee05-fdbf-406f-8aee-b451fd29ee46
MCP-Protocol-Version: 2025-06-18

{
  "jsonrpc": "2.0",
  "id": 0,
  "result": {
    "protocolVersion": "2025-06-18",
    "capabilities": {
      "tools": {}
    },
    "serverInfo": {
      "name": "mcp-server",
      "version": "1.0.0"
    }
  }
}
```

**What happened:**
- Claude sent the initialize request WITH the OAuth token
- **Server did NOT validate the token** (per MCP spec!)
- Server generated a unique session ID
- Server returned capabilities and session ID

**Critical insight:**
The logs show NO "Validating token" message here. This is the key fix - initialize must be accessible without token validation, even though Claude sends the token in the header.

### Step 3.2: Notification (Session Validation Only)

```
POST /
User-Agent: Claude-User
Authorization: Bearer eyJhbGciOiJkaXIiLCJlbmMi...
MCP-Session-ID: ed0fee05-fdbf-406f-8aee-b451fd29ee46  ← Now present!
MCP-Protocol-Version: 2025-06-18

{
  "method": "notifications/initialized",
  "jsonrpc": "2.0"
}
```

**Server logs:**
```
INFO - MCP request: method=notifications/initialized, id=None
INFO - Received initialized notification
DEBUG - Session validated: ed0fee05-fdbf-406f-8aee-b451fd29ee46
INFO - ✅ Session ed0fee05-fdbf-406f-8aee-b451fd29ee46 is now FULLY INITIALIZED
```

**Response:**
```
202 Accepted  ← Critical: This was the fix!
MCP-Session-ID: ed0fee05-fdbf-406f-8aee-b451fd29ee46
MCP-Protocol-Version: 2025-06-18
```

**What happened:**
- Claude sent notification that it's ready
- Server validated the SESSION ID (not the OAuth token)
- Server marked session as fully initialized
- Server returned 202 Accepted (not 204!)

**Critical insight:**
The server logged "Session validated" but NOT "Validating token". This proves the selective authentication is working - session check only, no OAuth validation.

### Step 3.3: Transport Detection

```
GET /
User-Agent: Claude-User
Accept: text/event-stream  ← Testing for SSE
MCP-Session-ID: ed0fee05-fdbf-406f-8aee-b451fd29ee46
MCP-Protocol-Version: 2025-06-18
```

**Response:**
```
405 Method Not Allowed  ← Critical: Not 501!
Allow: POST, HEAD, DELETE
MCP-Protocol-Version: 2025-06-18
```

**What happened:**
- Claude tested if the server supports SSE streaming
- Server returned 405 (Method Not Allowed)
- This tells Claude: "POST-only server, continue"

**Critical insight:**
If this returned 501 (Not Implemented), Claude would interpret it as "broken server" and terminate the session. The 405 + Allow header signals "this is intentional, use POST."

---

## Phase 4: Tool Operations (FIRST Authentication)

**Timestamp: 18:41:11.707788Z (milliseconds after handshake)**

### Step 4.1: List Tools (Full Authentication)

```
POST /
User-Agent: Claude-User
Authorization: Bearer eyJhbGciOiJkaXIiLCJlbmMi...
MCP-Session-ID: ed0fee05-fdbf-406f-8aee-b451fd29ee46
MCP-Protocol-Version: 2025-06-18

{
  "method": "tools/list",
  "params": {},
  "jsonrpc": "2.0",
  "id": 1
}
```

**Server logs:**
```
INFO - MCP request: method=tools/list, id=1
INFO - Listing available tools (requires authentication)
INFO - Validating token: eyJhbGciOiJkaXIiLCJl...1AfEF2yge-2rgSoxELAw  ← FIRST TIME!
DEBUG - Token key ID (kid): None
INFO - Token has no kid - using Auth0 userinfo for validation
INFO - Validating token via userinfo: https://your-tenant.auth0.com/userinfo
INFO - Token validated successfully via userinfo for subject: auth0|68e193461b57309d26362a05
INFO - Token scopes: ['mcp:read', 'mcp:execute']
INFO - Returning 4 tools
```

**What happened:**
1. Server detected this is a tool operation (requires auth)
2. **First time** token validation triggered
3. Token has no `kid` (it's JWE, not JWT)
4. Server called Auth0's userinfo endpoint for validation
5. Auth0 confirmed the token is valid
6. Server extracted scopes from validation response
7. Server returned the available MCP tools

**Response:**
```
200 OK
MCP-Session-ID: ed0fee05-fdbf-406f-8aee-b451fd29ee46

{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "tools": [
      {"name": "mcp_list", ...},
      {"name": "mcp_search", ...},
      {"name": "mcp_get_info", ...},
      {"name": "mcp_execute", ...}
    ]
  }
}
```

**Critical insight:**
This is THE moment where OAuth matters. The handshake completed WITHOUT token validation, but now that Claude is trying to use actual tools, full authentication kicks in.

---

## The Complete Flow Diagram

```
┌─────────────┐                                    ┌─────────────┐                    ┌─────────────┐
│  Claude.ai  │                                    │ MCP Server  │                    │   Auth0     │
│  (Client)   │                                    │ (Your API)  │                    │ (Auth Srv)  │
└──────┬──────┘                                    └──────┬──────┘                    └──────┬──────┘
       │                                                  │                                   │
       │ 1. HEAD / (Protocol check)                      │                                   │
       │────────────────────────────────────────────────>│                                   │
       │                                                  │                                   │
       │ 2. 200 OK (MCP-Protocol-Version: 2025-06-18)    │                                   │
       │<────────────────────────────────────────────────│                                   │
       │                                                  │                                   │
       │ 3. GET /.well-known/oauth-protected-resource    │                                   │
       │────────────────────────────────────────────────>│                                   │
       │                                                  │                                   │
       │ 4. 200 OK (Auth0 domain, scopes, etc)           │                                   │
       │<────────────────────────────────────────────────│                                   │
       │                                                  │                                   │
       │ 5. POST /oidc/register (Dynamic Client Reg)     │                                   │
       │─────────────────────────────────────────────────────────────────────────────────────>│
       │                                                  │                                   │
       │ 6. 201 Created (client_id)                      │                                   │
       │<─────────────────────────────────────────────────────────────────────────────────────│
       │                                                  │                                   │
       │ 7. GET /authorize (Authorization Request)       │                                   │
       │─────────────────────────────────────────────────────────────────────────────────────>│
       │                                                  │                                   │
       │         [User sees Auth0 login page]            │                                   │
       │         [User enters email/password]            │                                   │
       │         [User sees consent screen]              │                                   │
       │         [User clicks "Agree"]                   │                                   │
       │                                                  │                                   │
       │ 8. 302 Redirect (authorization code)            │                                   │
       │<─────────────────────────────────────────────────────────────────────────────────────│
       │                                                  │                                   │
       │ 9. POST /oauth/token (Token exchange)           │                                   │
       │─────────────────────────────────────────────────────────────────────────────────────>│
       │                                                  │                                   │
       │ 10. 200 OK (access_token: JWE)                  │                                   │
       │<─────────────────────────────────────────────────────────────────────────────────────│
       │                                                  │                                   │
       │ 11. POST / initialize (WITH token, NO validation)                                   │
       │────────────────────────────────────────────────>│                                   │
       │                                                  │                                   │
       │ 12. 200 OK (session_id, capabilities)           │                                   │
       │<────────────────────────────────────────────────│                                   │
       │                                                  │                                   │
       │ 13. POST / notifications/initialized (session only)                                 │
       │────────────────────────────────────────────────>│                                   │
       │                                                  │                                   │
       │ 14. 202 Accepted (session confirmed)            │                                   │
       │<────────────────────────────────────────────────│                                   │
       │                                                  │                                   │
       │ 15. GET / (SSE test)                            │                                   │
       │────────────────────────────────────────────────>│                                   │
       │                                                  │                                   │
       │ 16. 405 Method Not Allowed (POST-only)          │                                   │
       │<────────────────────────────────────────────────│                                   │
       │                                                  │                                   │
       │ 17. POST / tools/list (FIRST token validation)  │                                   │
       │────────────────────────────────────────────────>│                                   │
       │                                                  │                                   │
       │                                       18. POST /userinfo (validate token)           │
       │                                                  │──────────────────────────────────>│
       │                                                  │                                   │
       │                                       19. 200 OK (user info, scopes)                │
       │                                                  │<──────────────────────────────────│
       │                                                  │                                   │
       │ 20. 200 OK (4 tools)                            │                                   │
       │<────────────────────────────────────────────────│                                   │
       │                                                  │                                   │
       │ 21. POST / tools/call (execute calculator)      │                                   │
       │────────────────────────────────────────────────>│                                   │
       │                                                  │                                   │
       │                                       22. POST /userinfo (validate token)           │
       │                                                  │──────────────────────────────────>│
       │                                                  │                                   │
       │                                       23. 200 OK (validated)                        │
       │                                                  │<──────────────────────────────────│
       │                                                  │                                   │
       │ 24. 200 OK (calculation result)                 │                                   │
       │<────────────────────────────────────────────────│                                   │
       │                                                  │                                   │
```

---

## Why This Works: The Key Fixes

### Fix #1: Selective Authentication

**Before (Broken):**
```python
@app.post("/")
async def mcp_endpoint(token: Dict = Depends(verify_token)):
    # Token validated for ALL requests including initialize ❌
```

**After (Working):**
```python
@app.post("/")
async def mcp_endpoint(request: Request):
    body = await request.json()
    method = body.get('method')
    
    if method == 'initialize':
        # NO auth ✅
    elif method == 'notifications/initialized':
        # Session validation only ✅
    elif method in ['tools/list', 'tools/call']:
        # Full OAuth + session validation ✅
```

**Why it matters:**
- FastAPI's `Depends()` runs BEFORE the handler sees the request
- Can't conditionally skip based on method in request body
- Manual validation inside handler gives full control

### Fix #2: Correct Status Codes

**Before (Broken):**
```python
# notifications/initialized
return Response(status_code=204)  # ❌ Wrong

# GET / (SSE test)
return JSONResponse(status_code=501)  # ❌ Signals broken server
```

**After (Working):**
```python
# notifications/initialized  
return Response(status_code=202)  # ✅ Correct for notifications

# GET / (SSE test)
return JSONResponse(status_code=405)  # ✅ Signals POST-only server
```

**Why it matters:**
- MCP spec requires 202 for notifications with `id: null`
- 501 tells Claude "server is broken, terminate session"
- 405 tells Claude "POST-only server, continue normally"

### Fix #3: JWE Token Handling

**The logs reveal:**
```
DEBUG - Token key ID (kid): None
INFO - Token has no kid - using Auth0 userinfo for validation
```

**Why this matters:**
- Auth0 issued a JWE (encrypted) token, not JWT
- JWE tokens have no `kid` field
- Can't validate with JWKS (no key ID to look up)
- Must use Auth0's `/userinfo` endpoint instead

**Implementation:**
```python
async def verify_token_manual(request: Request) -> Dict:
    token = extract_token_from_header(request)
    
    try:
        header = jwt.get_unverified_header(token)
        kid = header.get("kid")
        
        if kid is None:
            # It's JWE, not JWT - use userinfo
            return validate_via_userinfo(token)
        else:
            # It's JWT - use JWKS
            return validate_with_jwks(token, kid)
    except:
        # Not even parseable as JWT - use userinfo
        return validate_via_userinfo(token)
```

---

## The Authentication Matrix

| MCP Method | OAuth Token? | Session ID? | First Seen In Logs |
|------------|--------------|-------------|--------------------|
| `initialize` | ❌ NO | ❌ NO | 18:41:11.561778Z |
| `notifications/initialized` | ❌ NO | ✅ YES | 18:41:11.647933Z |
| `tools/list` | ✅ YES | ✅ YES | 18:41:11.707788Z |
| `tools/call` | ✅ YES | ✅ YES | Later requests |
| `DELETE /` | ❌ NO | ✅ YES | Not in logs (no session termination) |
| `GET /` | N/A | N/A | 18:41:11.676911Z (returns 405) |

**Key observation from logs:**
- "Validating token" appears ONLY for `tools/list` (18:41:11.714523Z)
- NOT present for `initialize` or `notifications/initialized`
- This proves selective authentication is working correctly

---

## What Makes This Special

### 1. User-Agent Evolution
```
Discovery phase:  python-httpx/0.27.0  ← Claude's discovery client
After OAuth:      Claude-User           ← Claude's main client
```

This shows Claude switches clients after obtaining the token.

### 2. Parallel Requests
```
18:41:11.707788Z - tools/list
18:41:11.708513Z - resources/list  (milliseconds later)
18:41:11.727889Z - prompts/list    (20ms later)
```

Claude doesn't wait for responses - it fires multiple discovery requests in parallel for efficiency.

### 3. No Session Termination
After a successful connection, there's NO `DELETE /` request in the logs. This proves:
- The handshake succeeded
- Claude didn't encounter any errors
- The session continues normally

**Before the fixes, logs would show:**
```
18:41:11 - GET / → 501
18:41:11 - DELETE / ← Immediate termination
```

### 4. Token Validation Latency
```
18:41:11.714818Z - INFO - Validating token via userinfo
18:41:11.942268Z - INFO - Token validated successfully
```

**227 milliseconds** to validate the token via Auth0's userinfo endpoint. This is normal for external API calls and shows why JWE validation takes longer than local JWKS validation.

---

## Common Pitfalls (That Were Fixed)

### Pitfall #1: Authenticating initialize
**Symptom:** Claude disconnects immediately after OAuth
**Log evidence:** Would see "Validating token" for initialize
**Root cause:** FastAPI `Depends(verify_token)` on route decorator
**Fix:** Remove dependency, validate manually based on method

### Pitfall #2: Wrong status code for notifications
**Symptom:** Claude may retry or show warnings
**Log evidence:** 204 instead of 202 in response
**Root cause:** Misunderstanding MCP spec
**Fix:** Return 202 for notifications with `id: null`

### Pitfall #3: 501 for GET
**Symptom:** Claude terminates session after transport detection
**Log evidence:** GET returns 501, immediate DELETE follows
**Root cause:** Signaling "broken server" instead of "POST-only"
**Fix:** Return 405 with Allow header

### Pitfall #4: JWT-only validation
**Symptom:** Token validation fails with "no kid" error
**Log evidence:** "Token key ID (kid): None" followed by error
**Root cause:** Auth0 issued JWE, code only handled JWT
**Fix:** Fallback to userinfo validation for JWE tokens

---

## The Smoking Gun: What Success Looks Like

**In the logs, look for these indicators:**

✅ **Good Signs:**
```
INFO - Created MCP session: ed0fee05-... (fully initialized)
INFO - Session ed0fee05-... is now FULLY INITIALIZED
INFO - Token validated successfully via userinfo
INFO - Returning 4 tools
```

✅ **Correct Status Codes:**
```
200 - initialize
202 - notifications/initialized  ← Not 204!
405 - GET /                      ← Not 501!
200 - tools/list
```

✅ **Selective Authentication:**
```
NO "Validating token" for initialize
NO "Validating token" for notifications/initialized  
YES "Validating token" for tools/list  ← First time here!
```

✅ **No Premature Termination:**
- No DELETE request after GET
- Session continues
- Multiple tool requests succeed

---

## Conclusion

This handshake represents the first layer of a three-tier architecture:

1. **Discovery** (python-httpx): Claude finds your server and OAuth config
2. **Authentication** (User via browser): User authorizes Claude to access your server
3. **Operation** (Claude-User): Claude uses tools with validated tokens

The key innovation is **selective authentication**:
- Handshake methods (initialize, notifications) work WITHOUT token validation
- Tool operations (tools/list, tools/call) require FULL validation
- Session validation provides security WITHOUT blocking the handshake

After two days of debugging, the logs prove this approach works. The server now successfully:
- Complies with MCP protocol specification 2025-06-18
- Integrates with Auth0 for OAuth 2.1 with PKCE
- Handles both JWT and JWE tokens correctly
- Maintains sessions across multiple requests
- Enables Claude.ai to access MCP tools securely

**The handshake is complete. The tools are ready.** 🔒✅