# FederalRunner Auth0 Configuration Requirements

**Version:** 1.0.0
**Status:** Ready for Implementation
**Last Updated:** 2025-10-18
**Reference:** Auth0 Concepts (`docs/auth0/AUTH0_CONCEPTS.md`)

---

## Overview

This document defines the step-by-step requirements for configuring Auth0 as the OAuth 2.1 identity provider for FederalRunner MCP server. This enables Claude.ai and Claude Mobile to authenticate users and access federal form automation tools.

**Key Pattern**: Configure Auth0 with API, OAuth scopes, Dynamic Client Registration, and test applications for FederalRunner.

---

## REQ-AUTH0-001: Create Auth0 API (Protected Resource)

### Requirement

Create an Auth0 API that represents the FederalRunner MCP server as a protected resource.

### Steps

1. **Navigate to Auth0 Dashboard**
   - URL: https://manage.auth0.com/dashboard/
   - Login with your Auth0 account

2. **Create API**
   - Go to: **Applications** → **APIs**
   - Click: **Create API**

3. **Configure API Settings**
   ```
   Name: FederalRunner MCP Server
   Identifier: https://your-service.run.app
                (Use your actual Cloud Run URL once deployed)
                (For now, use placeholder: https://federalrunner-mcp-placeholder.run.app)
   Signing Algorithm: RS256
   ```

4. **Save and Note Credentials**
   After creation, the API settings page shows:
   - **Identifier (Audience)**: `https://your-service.run.app`
   - This will be used as `AUTH0_API_AUDIENCE` environment variable

### Key Concept: APIs vs Applications

**API (Protected Resource)**:
- **What**: The thing that IS protected and requires access tokens
- **Example**: FederalRunner MCP Server
- **Purpose**: Defines what resources need protection

**Application (OAuth Client)**:
- **What**: The thing that REQUESTS access to protected resources
- **Examples**: Claude MCP Client (created by Claude via DCR), Test Client (M2M for testing)
- **Purpose**: Represents who wants to use your API

**Relationship**: Application → Requests token → Gets token → Accesses API

### Identifier Update

⚠️ **IMPORTANT**: After deploying to Cloud Run and getting the actual URL, you must update the API Identifier:

1. Deploy to Cloud Run
2. Get actual URL: `https://federalrunner-mcp-xxx.run.app`
3. Update API Identifier in Auth0 dashboard
4. Update `AUTH0_API_AUDIENCE` environment variable in Cloud Run

### Reference

See: `docs/auth0/AUTH0_CONCEPTS.md` lines 6-24 (Applications vs APIs)

---

## REQ-AUTH0-002: Define OAuth Scopes

### Requirement

Define granular OAuth scopes for controlling access to FederalRunner tools.

### Scope Definitions

Navigate to: **Applications** → **APIs** → **FederalRunner MCP Server** → **Permissions** tab

Create these scopes:

| Scope | Description | Required For |
|-------|-------------|--------------|
| `federalrunner:read` | List wizards and get wizard info | `federalrunner_list_wizards`, `federalrunner_get_wizard_info` |
| `federalrunner:execute` | Execute wizards with user data | `federalrunner_execute_wizard` |

### Scope Usage

**Read-only operations**:
- `federalrunner_list_wizards()` - Discover available wizards
- `federalrunner_get_wizard_info()` - Get wizard schema (THE CONTRACT)

**Execution operations**:
- `federalrunner_execute_wizard()` - Fill forms and extract results

### Implementation in server.py

```python
async def execute_tool(tool_name: str, arguments: Dict, scopes: list) -> Dict:
    if tool_name == 'federalrunner_list_wizards':
        require_scope('federalrunner:read', scopes)
        # ... execute tool

    elif tool_name == 'federalrunner_get_wizard_info':
        require_scope('federalrunner:read', scopes)
        # ... execute tool

    elif tool_name == 'federalrunner_execute_wizard':
        require_scope('federalrunner:execute', scopes)
        # ... execute tool
```

---

## REQ-AUTH0-003: Enable Dynamic Client Registration (DCR)

### Requirement

Enable Dynamic Client Registration to allow Claude Android to register itself as an OAuth client at runtime.

### Why DCR is Needed

Claude Android uses Dynamic Client Registration (RFC 7591) to automatically create OAuth clients without manual pre-configuration by an administrator. When a user connects FederalRunner in Claude Mobile:

1. Claude calls Auth0's `/oidc/register` endpoint
2. Auth0 creates a new OAuth client for that user
3. Claude uses the client credentials for OAuth flow
4. User authenticates and authorizes access

Without DCR, you'd need to manually create an OAuth client for every Claude user—impossible at scale.

### Enable DCR

1. **Navigate to Settings**
   - Go to: **Applications** → **APIs** → **FederalRunner MCP Server**
   - Click: **Settings** tab

2. **Enable Dynamic Client Registration**
   - Scroll to: **Advanced Settings**
   - Expand: **OAuth**
   - Toggle ON: **Enable Dynamic Client Registration**
   - Registration Endpoint: `https://your-tenant.us.auth0.com/oidc/register`

3. **Configure DCR Policy**
   - Type: **Open** (allow anyone to register)
   - Security model: Enforced at API level, not registration level

### Security Model: Open DCR

**Is Open DCR Secure?**

YES - because security is enforced at the API level:

1. **Registration ≠ Access**: Anyone can register a client, but that doesn't grant access to your API
2. **Token Validation**: Your API validates every token (audience, issuer, signature, scopes)
3. **User Authorization**: Users explicitly authorize each client via consent screen
4. **Scope Enforcement**: Your API checks required scopes before executing tools

**Analogy**: Open DCR is like a hotel check-in kiosk where anyone can get a room key, but the key only works for rooms you're authorized to access.

### Reference

See: `docs/auth0/AUTH0_CONCEPTS.md` lines 29-51 (Dynamic Client Registration)

---

## REQ-AUTH0-004: Create Test Application (M2M)

### Requirement

Create a Machine-to-Machine (M2M) application for testing OAuth flows before Claude integration.

### Purpose

Test OAuth authentication and tool execution using curl/Postman before integrating with Claude.ai.

### Steps

1. **Create M2M Application**
   - Go to: **Applications** → **Applications**
   - Click: **Create Application**
   - Name: `FederalRunner Test Client`
   - Type: **Machine to Machine Applications**
   - Click: **Create**

2. **Authorize Application**
   - Select API: **FederalRunner MCP Server**
   - The next screen shows: "Authorize FederalRunner Test Client"
   - This asks: "Should this M2M app be able to access FederalRunner MCP Server?"
   - Click: **Authorize** (this is the critical step!)

3. **Select Scopes**
   - After authorizing, you see a list of permissions
   - Check ALL scopes:
     - ☑️ `federalrunner:read`
     - ☑️ `federalrunner:execute`
   - Click: **Update**

4. **Save Credentials**
   - Go back to the application's **Settings** tab
   - Note these values:
     ```
     Client ID: abc123...
     Client Secret: xyz789...
     ```
   - Save these to: `~/auth0-credentials-federalrunner.txt`

### Critical: M2M Pre-Authorization

⚠️ **IMPORTANT**: M2M applications (client_credentials grant) require **manual pre-authorization** in Auth0 dashboard.

**Why?**
- M2M flows have no user, so there's no consent screen
- Authorization must be granted in advance by the API administrator
- If you skip this step, token requests will fail with `access_denied`

**Steps to authorize:**
1. **Applications** → **APIs** → **FederalRunner MCP Server**
2. Click: **Machine To Machine Applications** tab
3. Find: **FederalRunner Test Client**
4. Toggle: **Authorized** (green)
5. Select scopes
6. Click: **Update**

### Testing with M2M Client

```bash
# Get access token
curl -X POST https://your-tenant.us.auth0.com/oauth/token \
  -H "Content-Type: application/json" \
  -d '{
    "client_id": "YOUR_CLIENT_ID",
    "client_secret": "YOUR_CLIENT_SECRET",
    "audience": "https://your-service.run.app",
    "grant_type": "client_credentials"
  }'

# Response:
{
  "access_token": "eyJ0eXAi...",
  "token_type": "Bearer",
  "expires_in": 86400
}

# Test MCP tools with token
curl -H "Authorization: Bearer eyJ0eXAi..." \
     https://your-service.run.app/
```

### Reference

See: `docs/auth0/AUTH0_CONCEPTS.md` lines 79-87 (client_credentials grant), lines 158-169 (authorization step)

---

## REQ-AUTH0-005: Create Test User

### Requirement

Create a test user for testing user-based OAuth flows (authorization_code grant).

### Purpose

Test the complete OAuth flow that Claude users will experience:
1. User clicks "Connect" in Claude.ai
2. Redirected to Auth0 login
3. Enter credentials
4. Consent screen
5. Token issued
6. Tools accessible

### Steps

1. **Create User**
   - Go to: **User Management** → **Users**
   - Click: **Create User**

2. **Configure User**
   ```
   Email: your-test-email@example.com
   Password: [Strong password - save it!]
   Connection: Username-Password-Authentication
   ```

3. **Save Credentials**
   Save to: `~/auth0-credentials-federalrunner.txt`
   ```
   Test User Email: your-test-email@example.com
   Test User Password: [password]
   ```

### Important: Two Separate Credential Systems

⚠️ **Auth0 Dashboard Account** (admin) is DIFFERENT from **Auth0 Application Users** (end users):

**Auth0 Dashboard Account**:
- Email/password for Auth0 dashboard access
- Purpose: Manage tenant, configure APIs, view logs
- NOT used for OAuth flows

**Auth0 Application Users**:
- Created in User Management → Users
- Purpose: Authenticate to use your application
- Used in OAuth flows
- Must be created separately (even if same email address)

### Testing User Flow

You can't easily test the full user flow locally, but once deployed to Cloud Run and integrated with Claude.ai:

1. Add connector in Claude.ai settings
2. Click "Connect"
3. Auth0 login page opens
4. Enter test user credentials
5. Consent screen shows requested scopes
6. Click "Allow"
7. Redirected back to Claude.ai
8. Tools are now accessible

### Reference

See: `docs/auth0/AUTH0_CONCEPTS.md` lines 88-97 (authorization_code grant), lines 122-130 (separate credential systems)

---

## REQ-AUTH0-006: Configure OAuth Metadata Endpoint

### Requirement

Implement `/.well-known/oauth-protected-resource` endpoint so Claude can discover Auth0 as the authorization server.

### Purpose

When Claude connects to FederalRunner MCP server, it needs to discover:
- Where to send users for authentication (Auth0)
- What scopes are available
- What token types are supported

This is automatic OAuth discovery per RFC 9728.

### Implementation in server.py

```python
@app.get("/.well-known/oauth-protected-resource")
async def oauth_metadata():
    """
    OAuth Protected Resource Metadata (RFC 9728).

    Required for Claude to discover Auth0 as the authorization server
    and initiate Dynamic Client Registration (DCR).
    """
    logger.info("OAuth metadata requested (for DCR discovery)")

    return {
        "resource": settings.MCP_SERVER_URL,
        "authorization_servers": [f"https://{settings.AUTH0_DOMAIN}"],
        "bearer_methods_supported": ["header"],
        "scopes_supported": ["federalrunner:read", "federalrunner:execute"]
    }
```

### Response Format

```json
{
  "resource": "https://federalrunner-mcp-xxx.run.app",
  "authorization_servers": ["https://your-tenant.us.auth0.com"],
  "bearer_methods_supported": ["header"],
  "scopes_supported": ["federalrunner:read", "federalrunner:execute"]
}
```

### How Claude Uses This

1. User adds FederalRunner connector in Claude.ai
2. Claude makes GET request to `/.well-known/oauth-protected-resource`
3. Claude discovers Auth0 URL from `authorization_servers`
4. Claude calls Auth0's `/oidc/register` to create OAuth client (DCR)
5. Claude initiates OAuth flow with user

---

## REQ-AUTH0-007: Environment Variables Configuration

### Requirement

Configure Auth0 environment variables for server.py.

### Required Variables

```bash
# Auth0 Domain (your tenant)
AUTH0_DOMAIN=your-tenant.us.auth0.com

# Auth0 Issuer (MUST end with trailing slash)
AUTH0_ISSUER=https://your-tenant.us.auth0.com/

# Auth0 API Audience (Cloud Run URL)
AUTH0_API_AUDIENCE=https://federalrunner-mcp-xxx.run.app

# MCP Server URL (same as audience)
MCP_SERVER_URL=https://federalrunner-mcp-xxx.run.app
```

### Critical: Trailing Slash on Issuer

⚠️ **IMPORTANT**: `AUTH0_ISSUER` MUST end with a trailing slash (`/`).

**Why?**
- JWT tokens contain an `iss` claim (issuer)
- Auth0 includes trailing slash in tokens
- Token validation compares `token.iss` == `AUTH0_ISSUER`
- Mismatch causes: "Invalid issuer" error

**Correct**:
```bash
AUTH0_ISSUER=https://your-tenant.us.auth0.com/
```

**Incorrect**:
```bash
AUTH0_ISSUER=https://your-tenant.us.auth0.com  # Missing trailing slash!
```

### Finding Your Values

1. **AUTH0_DOMAIN**:
   - Look at Auth0 dashboard URL
   - Format: `https://your-tenant.us.auth0.com/`
   - Extract: `your-tenant.us.auth0.com`

2. **AUTH0_ISSUER**:
   - Same as domain but with `https://` and trailing `/`
   - Format: `https://your-tenant.us.auth0.com/`

3. **AUTH0_API_AUDIENCE**:
   - Same as API Identifier you configured in REQ-AUTH0-001
   - After deployment: Your actual Cloud Run URL

4. **MCP_SERVER_URL**:
   - Same as AUTH0_API_AUDIENCE
   - This is where your MCP server is accessible

### Deployment Configuration

**Local Development** (`.env` file):
```bash
AUTH0_DOMAIN=your-tenant.us.auth0.com
AUTH0_ISSUER=https://your-tenant.us.auth0.com/
AUTH0_API_AUDIENCE=http://localhost:8080
MCP_SERVER_URL=http://localhost:8080
```

**Cloud Run** (deployment script):
```bash
gcloud run deploy federalrunner-mcp \
    --set-env-vars="AUTH0_DOMAIN=your-tenant.us.auth0.com" \
    --set-env-vars="AUTH0_ISSUER=https://your-tenant.us.auth0.com/" \
    --set-env-vars="AUTH0_API_AUDIENCE=https://federalrunner-mcp-xxx.run.app" \
    --set-env-vars="MCP_SERVER_URL=https://federalrunner-mcp-xxx.run.app"
```

---

## REQ-AUTH0-008: Save Credentials Securely

### Requirement

Save all Auth0 credentials in a secure location for reference.

### Credentials File

Create: `~/auth0-credentials-federalrunner.txt`

```
===========================================
FederalRunner Auth0 Credentials
===========================================

Auth0 Tenant: your-tenant.us.auth0.com

API Configuration:
  API Name: FederalRunner MCP Server
  API Identifier (Audience): https://federalrunner-mcp-xxx.run.app
  Scopes: federalrunner:read, federalrunner:execute

Test Application (M2M):
  Name: FederalRunner Test Client
  Client ID: abc123...
  Client Secret: xyz789...
  Grant Type: client_credentials

Test User:
  Email: your-test-email@example.com
  Password: [your-password]
  Purpose: Testing user OAuth flow

Environment Variables for Server:
  AUTH0_DOMAIN=your-tenant.us.auth0.com
  AUTH0_ISSUER=https://your-tenant.us.auth0.com/
  AUTH0_API_AUDIENCE=https://federalrunner-mcp-xxx.run.app
  MCP_SERVER_URL=https://federalrunner-mcp-xxx.run.app

Dynamic Client Registration:
  Enabled: Yes
  Endpoint: https://your-tenant.us.auth0.com/oidc/register
  Policy: Open (public registration)

Notes:
  - M2M client must be authorized in Auth0 dashboard
  - User client will be created by Claude via DCR
  - Update API Identifier after Cloud Run deployment
```

### Security

- Keep this file local (add to .gitignore)
- Don't commit to version control
- Use file permissions: `chmod 600 ~/auth0-credentials-federalrunner.txt`

---

## Configuration Checklist

### Phase 1: Auth0 Setup
- [ ] Create Auth0 account (if needed)
- [ ] Create API: FederalRunner MCP Server
- [ ] Set Identifier (placeholder URL initially)
- [ ] Define scopes: federalrunner:read, federalrunner:execute
- [ ] Enable Dynamic Client Registration
- [ ] Configure DCR as Open (public)

### Phase 2: Test Clients
- [ ] Create M2M test application
- [ ] Authorize M2M app for FederalRunner API
- [ ] Grant all scopes to M2M app
- [ ] Save Client ID and Secret
- [ ] Create test user account
- [ ] Save user credentials

### Phase 3: Server Configuration
- [ ] Add AUTH0 env vars to config.py
- [ ] Implement /.well-known/oauth-protected-resource endpoint
- [ ] Implement auth.py with OAuth 2.1 token validation
- [ ] Add require_scope() calls in execute_tool()
- [ ] Test token validation locally

### Phase 4: Post-Deployment
- [ ] Get actual Cloud Run URL
- [ ] Update API Identifier in Auth0
- [ ] Update AUTH0_API_AUDIENCE in Cloud Run
- [ ] Test M2M token flow
- [ ] Test user OAuth flow in Claude.ai

---

## Success Criteria

✅ Auth0 API created with correct identifier
✅ Scopes defined (federalrunner:read, federalrunner:execute)
✅ Dynamic Client Registration enabled
✅ M2M test application authorized and working
✅ Test user created and credentials saved
✅ OAuth metadata endpoint returns correct Auth0 config
✅ M2M token request succeeds
✅ Token validation works in server
✅ Scopes are properly enforced
✅ Claude.ai can discover Auth0 via DCR

---

## Troubleshooting

### Error: "access_denied" when requesting M2M token

**Cause**: M2M application not authorized for API

**Fix**:
1. Go to: Applications → APIs → FederalRunner MCP Server → Machine To Machine Applications
2. Find your test client
3. Toggle to "Authorized"
4. Select all scopes
5. Click Update

### Error: "Invalid issuer"

**Cause**: AUTH0_ISSUER doesn't have trailing slash

**Fix**: Add trailing slash to AUTH0_ISSUER environment variable

### Error: "Invalid audience"

**Cause**: AUTH0_API_AUDIENCE doesn't match API Identifier in Auth0

**Fix**: Ensure both are identical (usually your Cloud Run URL)

### Claude can't discover OAuth

**Cause**: /.well-known/oauth-protected-resource endpoint not implemented or returning wrong data

**Fix**:
1. Check endpoint is accessible
2. Verify it returns authorization_servers with Auth0 domain
3. Ensure scopes_supported matches your defined scopes

---

## References

- **Auth0 Concepts**: `docs/auth0/AUTH0_CONCEPTS.md`
- **Auth0 Implementation Guide**: `docs/auth0/AUTH0_IMPLEMENTATION_GUIDE.md`
- **OAuth 2.1 Spec**: https://oauth.net/2.1/
- **RFC 7591 (DCR)**: https://datatracker.ietf.org/doc/html/rfc7591
- **RFC 9728 (Metadata)**: https://datatracker.ietf.org/doc/html/rfc9728
