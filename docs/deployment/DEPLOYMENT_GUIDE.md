# FederalRunner MCP Server - Deployment Guide

**Version:** 1.0.0
**Last Updated:** 2025-10-19
**Service:** FederalRunner - Federal Form Wizard Automation
**Deployment Target:** Google Cloud Run

---

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Phase 1: Initial Deployment](#phase-1-initial-deployment)
4. [Phase 2: Auth0 Configuration](#phase-2-auth0-configuration)
5. [Phase 3: Update Deployment with Auth0](#phase-3-update-deployment-with-auth0)
6. [Phase 4: Claude.ai Integration](#phase-4-claudeai-integration)
7. [Phase 5: Testing & Validation](#phase-5-testing--validation)
8. [Troubleshooting](#troubleshooting)
9. [Maintenance & Updates](#maintenance--updates)

---

## Overview

This guide walks through deploying FederalRunner MCP server to Google Cloud Run with OAuth 2.1 authentication via Auth0.

### Architecture

```
┌─────────────────┐
│  Claude.ai /    │
│  Claude Mobile  │
└────────┬────────┘
         │ (1) Discover MCP server
         │ (2) OAuth via Auth0
         │ (3) Execute tools with token
         ▼
┌─────────────────────────────────┐
│  FederalRunner MCP Server       │
│  (Google Cloud Run)             │
│  - Validates OAuth tokens       │
│  - Executes wizards atomically  │
│  - Returns screenshots + data   │
└────────┬────────────────────────┘
         │ (4) Headless browser automation
         ▼
┌─────────────────────────────────┐
│  Federal Government Websites    │
│  - FSA Student Aid Estimator    │
│  - SSA Benefit Calculators      │
│  - IRS Tax Tools                │
└─────────────────────────────────┘
```

### Key Technologies

- **Container Platform**: Google Cloud Run (serverless, auto-scaling)
- **Authentication**: Auth0 OAuth 2.1 with Dynamic Client Registration (DCR)
- **Browser Automation**: Playwright (WebKit for headless compatibility)
- **Protocol**: MCP (Model Context Protocol) 2025-06-18
- **Transport**: Streamable HTTP (POST-only, no SSE)

---

## Prerequisites

### Required Accounts

- [ ] **Google Cloud Platform** account with billing enabled
- [ ] **Auth0** account (free tier works)
- [ ] **Claude.ai** Pro or Team subscription (for testing)

### Local Development Setup

- [ ] Python 3.11+ installed
- [ ] Google Cloud SDK (`gcloud`) installed and authenticated
- [ ] Docker Desktop (for local container testing)
- [ ] Git repository cloned

### Environment Verification

```bash
# Verify gcloud
gcloud --version
gcloud auth list
gcloud config get-value project

# Verify Python
python3 --version  # Should be 3.11+

# Verify Docker (optional, for local testing)
docker --version
```

---

## Phase 1: Initial Deployment

Deploy FederalRunner to Cloud Run to get the service URL, which is needed for Auth0 configuration.

### Step 1.1: Configure Project Settings

```bash
# Set your GCP project
export PROJECT_ID="your-gcp-project-id"
gcloud config set project $PROJECT_ID

# Enable required APIs
gcloud services enable run.googleapis.com
gcloud services enable cloudbuild.googleapis.com
gcloud services enable containerregistry.googleapis.com
```

### Step 1.2: Review Deployment Script

The `deploy.sh` script handles the complete deployment. Review key settings:

```bash
# View deployment configuration
cat deploy.sh
```

**Key Configuration**:
- **Service Name**: `federalrunner-mcp`
- **Region**: `us-central1` (change if needed)
- **Memory**: 2Gi
- **CPU**: 2
- **Timeout**: 60s (Playwright executions need time)
- **Concurrency**: 10 (limit concurrent browser instances)
- **Browser**: WebKit (headless compatible with FSA website)

### Step 1.3: Initial Deployment (No Auth0 Yet)

For the first deployment, we use placeholder Auth0 values to get the Cloud Run URL:

```bash
# Make script executable
chmod +x deploy.sh

# Deploy with placeholder values
./deploy.sh
```

**What Happens**:
1. Docker image built with Playwright + WebKit dependencies
2. Image pushed to Google Container Registry
3. Cloud Run service created
4. Public URL assigned: `https://federalrunner-mcp-XXXXX-uc.a.run.app`

### Step 1.4: Verify Initial Deployment

```bash
# Get service URL
export SERVICE_URL=$(gcloud run services describe federalrunner-mcp \
  --region=us-central1 \
  --format='value(status.url)')

echo "Service URL: $SERVICE_URL"

# Test health endpoint (should work without auth)
curl $SERVICE_URL/health

# Expected response:
# {
#   "status": "healthy",
#   "service": "federalrunner-mcp-server",
#   "version": "1.0.0"
# }
```

### Step 1.5: Save Service URL

```bash
# Save to file for reference
echo "FederalRunner Service URL: $SERVICE_URL" > ~/federalrunner-deployment.txt
echo "Deployment Date: $(date)" >> ~/federalrunner-deployment.txt
```

**Important**: You'll use this URL in Auth0 configuration in Phase 2.

---

## Phase 2: Auth0 Configuration

Configure Auth0 to provide OAuth 2.1 authentication for FederalRunner.

**Reference**: See `requirements/execution/AUTH0_CONFIGURATION_REQUIREMENTS.md` for detailed Auth0 setup instructions.

### Step 2.1: Create Auth0 API (Protected Resource)

1. Login to Auth0 Dashboard: https://manage.auth0.com/
2. Navigate to: **Applications** → **APIs**
3. Click: **Create API**

**Configuration**:
```
Name: FederalRunner MCP Server
Identifier: https://federalrunner-mcp-XXXXX-uc.a.run.app
           (Use your actual Cloud Run URL from Step 1.4)
Signing Algorithm: RS256
```

4. Click **Create**
5. Save the API Identifier (same as your Cloud Run URL)

### Step 2.2: Define OAuth Scopes

Navigate to: **APIs** → **FederalRunner MCP Server** → **Permissions** tab

Add these scopes:

| Scope | Description |
|-------|-------------|
| `federalrunner:read` | List wizards and get wizard schemas |
| `federalrunner:execute` | Execute wizards with user data |

Click **Add** for each scope.

### Step 2.3: Enable Dynamic Client Registration (DCR)

1. Go to: **APIs** → **FederalRunner MCP Server** → **Settings** tab
2. Scroll to: **Advanced Settings**
3. Expand: **OAuth**
4. Toggle ON: **Enable Dynamic Client Registration**
5. Set Type: **Open** (allow Claude to self-register)
6. Click **Save Changes**

**Why Open DCR?**
Claude Android needs to create OAuth clients automatically when users connect. Security is enforced at the API level (token validation, scopes), not at registration.

### Step 2.4: Create Test Application (M2M)

For testing OAuth before Claude integration:

1. Navigate to: **Applications** → **Applications**
2. Click: **Create Application**
3. Configure:
   ```
   Name: FederalRunner Test Client
   Type: Machine to Machine Applications
   ```
4. Click **Create**
5. Select API: **FederalRunner MCP Server**
6. Click **Authorize**
7. Select ALL scopes:
   - ☑ `federalrunner:read`
   - ☑ `federalrunner:execute`
8. Click **Update**

**Save Credentials**:
- Go to application **Settings** tab
- Note **Client ID** and **Client Secret**
- Save to `~/auth0-credentials-federalrunner.txt`

### Step 2.5: Create Test User

1. Navigate to: **User Management** → **Users**
2. Click: **Create User**
3. Configure:
   ```
   Email: your-test-email@example.com
   Password: [Strong password]
   Connection: Username-Password-Authentication
   ```
4. Click **Create**
5. Save credentials to `~/auth0-credentials-federalrunner.txt`

### Step 2.6: Save All Auth0 Credentials

Create: `~/auth0-credentials-federalrunner.txt`

```
===========================================
FederalRunner Auth0 Credentials
===========================================

Auth0 Tenant: your-tenant.us.auth0.com

API Configuration:
  API Name: FederalRunner MCP Server
  API Identifier (Audience): https://federalrunner-mcp-XXXXX-uc.a.run.app
  Scopes: federalrunner:read, federalrunner:execute

Test Application (M2M):
  Name: FederalRunner Test Client
  Client ID: [your-client-id]
  Client Secret: [your-client-secret]
  Grant Type: client_credentials

Test User:
  Email: your-test-email@example.com
  Password: [your-password]

Environment Variables:
  AUTH0_DOMAIN=your-tenant.us.auth0.com
  AUTH0_ISSUER=https://your-tenant.us.auth0.com/
  AUTH0_API_AUDIENCE=https://federalrunner-mcp-XXXXX-uc.a.run.app
  MCP_SERVER_URL=https://federalrunner-mcp-XXXXX-uc.a.run.app

Dynamic Client Registration:
  Enabled: Yes
  Endpoint: https://your-tenant.us.auth0.com/oidc/register
```

**Security**: Set file permissions: `chmod 600 ~/auth0-credentials-federalrunner.txt`

---

## Phase 3: Update Deployment with Auth0

Re-deploy FederalRunner with real Auth0 credentials.

### Step 3.1: Update deploy.sh with Auth0 Values

Edit `deploy.sh` and replace placeholder values with your Auth0 credentials:

```bash
# From ~/auth0-credentials-federalrunner.txt
AUTH0_DOMAIN="your-tenant.us.auth0.com"
AUTH0_ISSUER="https://your-tenant.us.auth0.com/"
AUTH0_API_AUDIENCE="https://federalrunner-mcp-XXXXX-uc.a.run.app"
MCP_SERVER_URL="https://federalrunner-mcp-XXXXX-uc.a.run.app"
```

**Critical**: Ensure `AUTH0_ISSUER` has trailing slash!

### Step 3.2: Redeploy with Auth0

```bash
./deploy.sh
```

This updates the Cloud Run service with Auth0 environment variables.

### Step 3.3: Verify Auth0 Integration

```bash
# Test OAuth metadata endpoint (should work without auth)
curl $SERVICE_URL/.well-known/oauth-protected-resource

# Expected response:
# {
#   "resource": "https://federalrunner-mcp-XXXXX-uc.a.run.app",
#   "authorization_servers": ["https://your-tenant.us.auth0.com"],
#   "bearer_methods_supported": ["header"],
#   "scopes_supported": ["federalrunner:read", "federalrunner:execute"]
# }
```

### Step 3.4: Test M2M Token Flow

```bash
# Get access token from Auth0
curl -X POST https://your-tenant.us.auth0.com/oauth/token \
  -H "Content-Type: application/json" \
  -d '{
    "client_id": "YOUR_M2M_CLIENT_ID",
    "client_secret": "YOUR_M2M_CLIENT_SECRET",
    "audience": "https://federalrunner-mcp-XXXXX-uc.a.run.app",
    "grant_type": "client_credentials"
  }'

# Save the access_token from response
export ACCESS_TOKEN="eyJ0eXAi..."

# Test MCP initialize (no auth required)
curl -X POST $SERVICE_URL/ \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
      "protocolVersion": "2025-06-18",
      "capabilities": {},
      "clientInfo": {
        "name": "test-client",
        "version": "1.0.0"
      }
    }
  }'

# Response includes MCP-Session-ID header
# Save SESSION_ID from response header

# Test tools/list (requires auth)
curl -X POST $SERVICE_URL/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "MCP-Session-ID: $SESSION_ID" \
  -d '{
    "jsonrpc": "2.0",
    "id": 2,
    "method": "tools/list",
    "params": {}
  }'

# Expected: List of 3 tools (federalrunner_list_wizards, etc.)
```

---

## Phase 4: Claude.ai Integration

Configure FederalRunner as a remote MCP server in Claude.ai.

### Step 4.1: Add Remote Server in Claude.ai

1. Go to: https://claude.ai/
2. Click your profile → **Settings**
3. Navigate to: **Developers** → **MCP Servers**
4. Click: **Add Remote Server**

**Configuration**:
```
Server Name: FederalRunner
Server URL: https://federalrunner-mcp-XXXXX-uc.a.run.app
Authentication: OAuth 2.1
```

5. Click **Connect**

### Step 4.2: Authorize via Auth0

1. Claude redirects to Auth0 login page
2. Enter test user credentials (from Step 2.5)
3. Review consent screen showing requested scopes:
   - `federalrunner:read`
   - `federalrunner:execute`
4. Click **Allow**
5. Redirected back to Claude.ai
6. Connection status shows: **Connected**

### Step 4.3: Verify Tools Available

In Claude.ai chat:

```
You: What tools do you have access to?

Claude: I have access to FederalRunner tools:
- federalrunner_list_wizards
- federalrunner_get_wizard_info
- federalrunner_execute_wizard
```

### Step 4.4: Test Basic Workflow

```
You: List available federal form wizards

Claude: [Calls federalrunner_list_wizards]
I found 1 wizard:
- fsa-estimator: FSA Student Aid Estimator (7 pages)

You: Get info for fsa-estimator

Claude: [Calls federalrunner_get_wizard_info]
The FSA Student Aid Estimator requires these fields:
[Shows schema with all required fields]

You: I'm a student born May 15, 2003, unmarried, living with parents
     in Illinois. My parents are married with income $85,000...

Claude: [Calls federalrunner_execute_wizard with collected data]
[Shows screenshots of filled forms and extracted results]
```

---

## Phase 5: Testing & Validation

### Step 5.1: Functional Testing

**Test Case 1: List Wizards**
```
Input: "List available wizards"
Expected: Returns fsa-estimator metadata
Validates: federalrunner:read scope enforcement
```

**Test Case 2: Get Schema**
```
Input: "Get info for fsa-estimator"
Expected: Returns complete User Data Schema
Validates: Schema loading and enhancement
```

**Test Case 3: Execute Wizard**
```
Input: Complete user data for FSA estimator
Expected:
  - Validation passes
  - Browser launches (WebKit, headless)
  - All 7 pages filled
  - Screenshots captured
  - Results extracted
Validates:
  - federalrunner:execute scope
  - Atomic execution pattern
  - WebKit headless compatibility
```

### Step 5.2: Performance Validation

Check Cloud Run metrics:

1. Go to: Google Cloud Console → Cloud Run
2. Select: `federalrunner-mcp`
3. View: **Metrics** tab

**Expected Metrics**:
- Request latency: 8-15 seconds (Playwright execution)
- Memory usage: ~1.5Gi peak (WebKit browser)
- CPU usage: ~1.8 CPUs during execution
- Cold start: ~5-8 seconds (Playwright initialization)

### Step 5.3: Mobile Testing (Claude Android/iOS)

1. Install Claude mobile app
2. Add FederalRunner connector in app settings
3. Test voice workflow:
   ```
   "I need to estimate my financial aid for college. I'm a dependent
   student born May 15, 2003, unmarried, living with my parents in
   Illinois. They're married with a household income of $85,000,
   no other income, and about $12,000 in bank accounts. I'm planning
   to attend a public 4-year college in Illinois."
   ```
4. Verify:
   - OAuth flow works on mobile
   - Tool execution succeeds
   - Screenshots display properly
   - Results are readable

---

## Troubleshooting

### Error: "Invalid issuer"

**Symptom**: Token validation fails with "Invalid issuer" error

**Cause**: `AUTH0_ISSUER` doesn't have trailing slash

**Fix**:
```bash
# Check current value
gcloud run services describe federalrunner-mcp --region=us-central1 \
  --format='value(spec.template.spec.containers[0].env[?name=="AUTH0_ISSUER"].value)'

# Should be: https://your-tenant.us.auth0.com/
# If missing slash, redeploy with corrected value
```

### Error: "Invalid audience"

**Symptom**: Token validation fails with "Invalid audience" error

**Cause**: `AUTH0_API_AUDIENCE` doesn't match API Identifier in Auth0

**Fix**:
1. Check Auth0: **APIs** → **FederalRunner MCP Server** → API Identifier
2. Check Cloud Run env var: `AUTH0_API_AUDIENCE`
3. Ensure both are identical (your Cloud Run URL)
4. Update mismatch and redeploy

### Error: "access_denied" when requesting M2M token

**Symptom**: Auth0 returns `access_denied` error for M2M token request

**Cause**: M2M application not authorized for API

**Fix**:
1. Go to: **APIs** → **FederalRunner MCP Server** → **Machine To Machine Applications**
2. Find: FederalRunner Test Client
3. Toggle to: **Authorized**
4. Select all scopes
5. Click **Update**
6. Retry token request

### Error: Browser fails in headless mode

**Symptom**: Playwright execution fails with browser errors in Cloud Run

**Cause**: Using Chromium instead of WebKit (FSA blocks headless Chromium)

**Fix**:
```bash
# Verify BROWSER_TYPE is set to webkit in deploy.sh
grep BROWSER_TYPE deploy.sh

# Should show: BROWSER_TYPE="webkit"
# If not, update and redeploy
```

### Error: Memory exceeded / OOM

**Symptom**: Cloud Run container terminated with "Memory limit exceeded"

**Cause**: WebKit browser + Playwright consuming too much memory

**Fix**:
```bash
# Increase memory allocation in deploy.sh
# Change from 2Gi to 4Gi
--memory 4Gi

# Also reduce concurrency to limit simultaneous browser instances
--concurrency 5
```

### Claude.ai can't discover server

**Symptom**: Claude shows "Unable to connect to server" error

**Cause**: OAuth metadata endpoint not accessible or returning wrong data

**Fix**:
```bash
# Test metadata endpoint
curl $SERVICE_URL/.well-known/oauth-protected-resource

# Verify response has:
# - authorization_servers: [your Auth0 domain]
# - scopes_supported: [your defined scopes]

# Check Cloud Run logs for errors
gcloud run services logs read federalrunner-mcp --region=us-central1 --limit=50
```

### Logs Investigation

```bash
# Stream live logs
gcloud run services logs tail federalrunner-mcp --region=us-central1

# View recent errors
gcloud run services logs read federalrunner-mcp \
  --region=us-central1 \
  --limit=100 \
  --format="value(textPayload)" \
  | grep "ERROR"

# View specific request by session ID
gcloud run services logs read federalrunner-mcp \
  --region=us-central1 \
  --limit=200 \
  | grep "session-id-here"
```

---

## Maintenance & Updates

### Updating Code

```bash
# Make code changes locally
# Test locally if needed

# Redeploy (automatically builds new image)
./deploy.sh

# Verify deployment
curl $SERVICE_URL/health
```

### Adding New Wizards

When FederalScout discovers new wizards:

```bash
# Ensure new wizard files are in ../../wizards/
# - wizard-structures/new-wizard.json
# - data-schemas/new-wizard-schema.json

# Redeploy to copy new wizard files into container
./deploy.sh

# Verify new wizard appears
curl -X POST $SERVICE_URL/ \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "MCP-Session-ID: $SESSION_ID" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/call",
    "params": {
      "name": "federalrunner_list_wizards",
      "arguments": {}
    }
  }'
```

### Monitoring Best Practices

1. **Set up Cloud Monitoring alerts**:
   - High error rate (> 5%)
   - High latency (> 30s)
   - Memory near limit (> 90%)

2. **Review Auth0 logs weekly**:
   - Failed login attempts
   - Unusual token request patterns
   - New client registrations

3. **Check wizard success rates**:
   - Parse logs for execution failures
   - Identify selectors that break
   - Update wizard structures as needed

### Cost Optimization

**Current Cost Estimate** (based on usage):
- Cloud Run: $0.00 (within free tier for light usage)
- Auth0: $0.00 (free tier)
- Artifact Registry: ~$0.10/month (image storage)

**For production scale**:
- Set up min instances = 0 (default) to scale to zero
- Set max instances = 10 to limit concurrent costs
- Use concurrency = 10 to maximize container reuse

---

## Success Criteria

**Phase 1 - Initial Deployment**:
- ✅ Cloud Run service deployed
- ✅ Service URL obtained
- ✅ Health endpoint responds

**Phase 2 - Auth0 Configuration**:
- ✅ Auth0 API created
- ✅ Scopes defined
- ✅ DCR enabled
- ✅ M2M test client authorized
- ✅ Test user created

**Phase 3 - Auth0 Integration**:
- ✅ Service redeployed with Auth0 env vars
- ✅ OAuth metadata endpoint works
- ✅ M2M token flow succeeds
- ✅ Token validation works

**Phase 4 - Claude Integration**:
- ✅ Claude.ai connector configured
- ✅ OAuth authorization flow succeeds
- ✅ Tools visible in Claude
- ✅ Basic workflow executes

**Phase 5 - Production Validation**:
- ✅ All test cases pass
- ✅ Performance metrics acceptable
- ✅ Mobile apps work
- ✅ Logs show successful executions

---

## Next Steps

After successful deployment:

1. **Document user workflows** for common scenarios
2. **Add more wizards** (SSA, IRS calculators)
3. **Implement result extraction** (wizard-specific parsing)
4. **Create demo video** for blog post
5. **Monitor usage patterns** and optimize

---

## References

- **Auth0 Configuration**: `requirements/execution/AUTH0_CONFIGURATION_REQUIREMENTS.md`
- **MCP Specification**: https://modelcontextprotocol.io/specification/2025-06-18
- **OAuth 2.1 Spec**: https://oauth.net/2.1/
- **Cloud Run Docs**: https://cloud.google.com/run/docs
- **Playwright Docs**: https://playwright.dev/python/
