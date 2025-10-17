# Auth0 Remote MCP Server Deployment - Key Learnings

## Auth0 Core Concepts

### Applications vs APIs

**Applications (OAuth Clients)**
- **What**: Things that REQUEST access to protected resources
- **Think**: "Who wants to use your API?"
- **Examples**: 
  - MDCalc Test Client (your M2M app for testing)
  - Claude MCP Client (created by Claude via DCR in production)

**APIs (Protected Resources)**
- **What**: Things that ARE protected and require access tokens
- **Think**: "What needs protection?"
- **Examples**:
  - MDCalc MCP API (your MCP server endpoints)
  - Auth0 Management API (controls Auth0 tenant settings)

### The Relationship
```
Application → Requests token → Gets token → Accesses API
```

---

## Dynamic Client Registration (DCR)

### What It Is
Allows applications to register themselves as OAuth clients at runtime instead of being pre-configured by an administrator.

### Open vs Protected DCR

**Open DCR** (what you enabled):
- Anyone can call `/oidc/register` to create a client
- No authentication required for registration
- Security enforced at API level, not registration level

**Security Model**:
- Registering a client ≠ Access to your API
- Your API validates tokens (audience, issuer, scopes)
- Random registrations can't access protected resources

### How It Works
```
Claude Android → POST /oidc/register → Auth0 creates client → Returns Client ID
```

No credentials needed for Open DCR - it's like a hotel check-in kiosk where anyone can get a room key, but the key only works for rooms you're authorized to access.

---

## Authentication Credentials

### What You Saved in `~/auth0-credentials.txt`

**Used by MCP Server** (required):
- `AUTH0_DOMAIN` - For fetching JWKS (public keys)
- `AUTH0_ISSUER` - To verify token's `iss` claim
- `AUTH0_API_AUDIENCE` - To verify token's `aud` claim
- `MCP_SERVER_URL` - For OAuth metadata endpoint

**NOT Used by MCP Server** (saved for reference only):
- `AUTH0_CLIENT_ID` - M2M application credential
- `AUTH0_CLIENT_SECRET` - M2M application credential  
- `AUTH0_TENANT` - Redundant with domain

### Why Client ID/Secret Aren't Needed

Your MCP server **validates tokens**, it doesn't create them. Token validation only needs public keys (fetched from Auth0) and expected issuer/audience values.

You'd only need Client ID/Secret if your server was creating its own tokens or calling Auth0 Management API.

---

## Grant Types & Authorization

### client_credentials (M2M - Your Test Client)
- No user involved
- No consent screen
- Requires **manual pre-authorization** in Auth0 dashboard
- Application → API relationship configured explicitly
- Error if not pre-authorized: `access_denied`

### authorization_code (User-based - Claude Android)
- User involved in flow
- Shows **consent screen** to user
- User authorization = API access granted
- No pre-authorization needed in dashboard
- User clicks "Allow" on consent screen

---

## User Authorization in Free Tier

### What Auth0 Free Tier Provides
- API-level controls: Which applications can access which APIs ✓
- Scope definitions ✓

### What's Missing in Free Tier
- User-to-API assignment ✗
- User-level scope restrictions ✗
- Role-based API access ✗

### How User Access Works

**Any user in your tenant can authorize any client** via consent screen. Access control options:

1. **Consent screen** - User clicks "Allow" or "Deny" (built-in)
2. **Auth0 Actions** - JavaScript runs during token issuance (free tier available)
3. **Application logic** - Your server checks user permissions (most common)
4. **Paid tier** - RBAC and fine-grained authorization

---

## Two Separate Credential Systems

### Auth0 Dashboard Account (Admin)
- Email/password for Auth0 dashboard access
- Purpose: Manage tenant, configure APIs, view logs
- NOT used for OAuth flows

### Auth0 Application Users (End Users)
- Created in User Management → Users
- Purpose: Authenticate to use your application
- Used in OAuth flows
- Must be created separately (even if same email address)

---

## The Complete OAuth Flow

### Testing Flow (Your M2M App)
```
1. You → curl with Client ID/Secret
2. Auth0 checks: Is client authorized for this API?
3. Auth0 issues token (if authorized)
4. You → Call MCP server with token
5. Server validates token
```

### Production Flow (Claude Android)
```
1. Claude → DCR → Gets Client ID
2. User clicks "Connect" → OAuth flow starts
3. User → Auth0 login → Enters application user credentials
4. Auth0 → Shows consent screen with requested scopes
5. User → Clicks "Allow"
6. Auth0 → Issues token to Claude
7. Claude → Calls MCP server with token
8. Server → Validates token (signature, issuer, audience, scopes)
```

---

## Critical Authorization Step

To allow M2M applications to get tokens for your API:

**Applications → APIs → [Your API] → Machine To Machine Applications tab**
- Toggle application to "Authorized"
- Select required scopes
- Click "Update"

Without this, M2M `client_credentials` requests fail with `access_denied`.

User-based flows (like Claude Android) don't need this because user consent provides authorization.

---

## Key Security Points

1. **Open DCR is acceptable** - Security is at the API level, not registration
2. **Token validation is critical** - Always verify issuer, audience, signature, scopes
3. **Consent screen protects users** - Users explicitly authorize each client
4. **M2M apps need pre-authorization** - Must be configured in dashboard
5. **User apps get authorized via consent** - No dashboard configuration needed