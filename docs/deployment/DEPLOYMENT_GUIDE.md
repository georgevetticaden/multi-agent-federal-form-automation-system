# MDCalc MCP Server - Cloud Run Deployment Guide

Complete guide for deploying the MDCalc MCP Server to Google Cloud Run with OAuth 2.1 authentication and MDCalc session management.

---

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Configuration Setup](#configuration-setup)
4. [Authentication State Management](#authentication-state-management)
5. [Deployment Process](#deployment-process)
6. [Monitoring & Troubleshooting](#monitoring--troubleshooting)
7. [Maintenance](#maintenance)
8. [Security & Cost](#security--cost)

---

## Overview

This deployment guide covers two main aspects:

1. **Infrastructure Configuration** - Google Cloud project, Auth0, resource allocation
2. **Authentication Management** - MDCalc session state via Google Secret Manager

### Architecture

```
┌─────────────────┐    OAuth 2.1     ┌─────────────────┐
│ Claude Android  │ ──────────────> │     Auth0       │
│  (or client)    │ <────────────── │  (Token Issuer) │
└─────────────────┘   Access Token   └─────────────────┘
         │                                    ▲
         │ Authenticated Requests             │ JWKS
         ▼                                    │ Validation
┌─────────────────────────────────────────────┐
│  MDCalc MCP Server (Cloud Run)             │ ────┘
│  • OAuth 2.1 token validation              │
│  • Scope-based authorization               │
│  • Headless browser automation             │
│  • MDCalc auth state from Secret Manager   │
└─────────────────────────────────────────────┘
         │
         ▼
┌─────────────────┐
│   MDCalc.com    │
│  (825+ calcs)   │
└─────────────────┘
```

---

## Prerequisites

### 1. Google Cloud Account

- Active Google Cloud project
- Billing enabled
- `gcloud` CLI installed and authenticated

```bash
# Install gcloud CLI (if not already installed)
# https://cloud.google.com/sdk/docs/install

# Authenticate
gcloud auth login

# Verify
gcloud config list
```

### 2. Auth0 Account

- Auth0 tenant created
- API configured with scopes
- Dynamic Client Registration (DCR) enabled

**Setup steps:**
1. Go to [Auth0 Dashboard](https://manage.auth0.com/)
2. Create API: Applications → APIs → Create API
   - Name: `MDCalc MCP Server`
   - Identifier: `https://mdcalc-mcp-server` (temporary, will update after deployment)
   - Scopes: `mdcalc:read`, `mdcalc:calculate`
3. Enable DCR: Applications → Advanced → OAuth → Enable Dynamic Client Registration

---

## Configuration Setup

### Step 1: Create Deployment Configuration

The deployment script uses `.env.deployment` for all configuration.

```bash
cd mcp-servers/mdcalc-automation-mcp

# Copy template
cp .env.deployment.example .env.deployment

# Edit with your values
nano .env.deployment
```

### Step 2: Configure Parameters

```bash
# Google Cloud Configuration
PROJECT_ID=your-project-id                  # Find in GCP Console → Dashboard
REGION=us-central1                          # Closest region to your users
SERVICE_NAME=mdcalc-mcp-server             # Name for Cloud Run service

# Auth0 Configuration
AUTH0_DOMAIN=your-tenant.us.auth0.com      # From Auth0 Dashboard → Settings
AUTH0_ISSUER=https://your-tenant.us.auth0.com/  # Same domain with https:// and trailing /

# Secret Manager Configuration
SECRET_NAME=mdcalc-auth-state              # Name for MDCalc session secret

# Cloud Run Resources
MEMORY=2Gi                                  # 512Mi, 1Gi, 2Gi, 4Gi, 8Gi
CPU=2                                       # 1, 2, 4, 8 (must be ≤ memory in Gi)
TIMEOUT=300                                 # 1-3600 seconds
MIN_INSTANCES=0                             # 0 = scale to zero (saves cost)
MAX_INSTANCES=10                            # Max concurrent instances

# Local Configuration
AUTH_STATE_FILE=../../recordings/auth/mdcalc_auth_state.json
```

### Step 3: Parameter Details

#### Google Cloud Settings

**PROJECT_ID**
- Your Google Cloud project identifier (NOT the project name)
- Find: GCP Console → Click project dropdown → Copy "Project ID"
- Example: `my-project-123456`

**REGION**
- Geographic region for deployment
- Options: `us-central1` (Iowa), `us-east1` (South Carolina), `us-west1` (Oregon)
- Choose closest to your users for lowest latency

**SERVICE_NAME**
- Name for your Cloud Run service
- Becomes part of URL: `https://SERVICE_NAME-{hash}-{region}.a.run.app`
- Rules: lowercase letters, numbers, hyphens only

#### Auth0 Settings

**AUTH0_DOMAIN**
- Your Auth0 tenant domain
- Format: `{tenant}.{region}.auth0.com` (NO `https://`)
- Find: Auth0 Dashboard → Settings → Domain
- Example: `dev-abc123xyz.us.auth0.com`

**AUTH0_ISSUER**
- Auth0 token issuer URL
- Format: `https://{AUTH0_DOMAIN}/` (WITH `https://` and trailing slash)
- Example: `https://dev-abc123xyz.us.auth0.com/`

#### Resource Settings

**MEMORY**
- RAM per instance
- Recommendation: `2Gi` for production (Chrome needs at least 1Gi)
- Higher memory = higher cost

**CPU**
- vCPUs per instance
- Must be ≤ memory in Gi (e.g., 2Gi → max 2 CPUs)
- Recommendation: `2` for production

**TIMEOUT**
- Max request duration (1-3600 seconds)
- Recommendation: `300` (5 minutes) - calculator execution can take 10-15 seconds

**MIN_INSTANCES** / **MAX_INSTANCES**
- `MIN_INSTANCES=0` → Scale to zero (saves money, has cold starts)
- `MIN_INSTANCES=1` → Always warm (costs ~$12/month, no cold starts)
- `MAX_INSTANCES=10` → Sufficient for most use cases

#### Service Account

The deployment script uses the **Compute Engine default service account**:
- **Format**: `{PROJECT_NUMBER}-compute@developer.gserviceaccount.com`
- **Pre-existing**: Automatically created in every Google Cloud project
- **Purpose**: Cloud Run instances run as this account
- **Permissions granted**: `roles/secretmanager.secretAccessor` (read-only access to mdcalc-auth-state secret)

**NOT created by the deployment script** - it already exists!

---

## Authentication State Management

### The Problem

MDCalc blocks headless browsers using bot detection. We need an authenticated session to bypass this.

### The Solution

Use **Google Secret Manager** to securely store and manage MDCalc authentication state.

```
┌─────────────────────────────────────────────────────────────────┐
│                     Development Environment                      │
│  1. Manual Login → tools/recording-generator/manual_login.py   │
│     Creates: recordings/auth/mdcalc_auth_state.json            │
│  2. Upload → scripts/deploy-to-cloud-run.sh                    │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Google Secret Manager                         │
│  Secret: mdcalc-auth-state                                      │
│  Mounted to Cloud Run: /app/auth/mdcalc_auth_state.json        │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Cloud Run Instance                          │
│  Playwright uses auth state to bypass bot detection             │
└─────────────────────────────────────────────────────────────────┘
```

### Create Authentication State

```bash
cd tools/recording-generator
python manual_login.py
```

This will:
1. Open Firefox browser
2. Navigate to MDCalc
3. Prompt you to log in manually
4. Save session to `recordings/auth/mdcalc_auth_state.json`

**Session lifespan**: 30-90 days (needs periodic refresh)

---

## Deployment Process

### Step 1: Verify Prerequisites

```bash
# 1. Check auth state exists
ls -lh ../../recordings/auth/mdcalc_auth_state.json

# 2. Check .env.deployment configured
cat .env.deployment

# 3. Verify gcloud authenticated
gcloud auth list
gcloud config get-value project
```

### Step 2: Run Deployment Script

```bash
cd mcp-servers/mdcalc-automation-mcp
./scripts/deploy-to-cloud-run.sh
```

**What about Docker?** The script uses `--source .` which tells Cloud Run to:
1. Automatically detect the `Dockerfile` in the current directory
2. Upload source code to Google Cloud Build
3. Build the Docker image using your Dockerfile
4. Push image to Google Container Registry
5. Deploy the image to Cloud Run

**You don't need to build Docker images manually!** Cloud Run does it all for you.

### Step 3: What the Script Does

```
✅ Step 1: Load configuration from .env.deployment
✅ Step 2: Verify auth state file exists
✅ Step 3: Set Google Cloud project
✅ Step 4: Enable required APIs
   - Cloud Run API
   - Secret Manager API
   - Cloud Build API
✅ Step 5: Create/update Secret Manager secret
   - Upload mdcalc_auth_state.json
✅ Step 6: Get Cloud Run service account
   - Format: {PROJECT_NUMBER}-compute@developer.gserviceaccount.com
✅ Step 7: Grant secret access to service account
   - Role: roles/secretmanager.secretAccessor
✅ Step 8: Deploy to Cloud Run
   - Build container from source
   - Mount secret at /app/auth/mdcalc_auth_state.json
   - Set environment variables
   - Configure resources (memory, CPU, timeout)
✅ Step 9: Get service URL
✅ Step 10: Update AUTH0_API_AUDIENCE environment variable
✅ Step 11: Test deployment
   - Health endpoint: /health
   - OAuth metadata: /.well-known/oauth-protected-resource
```

**Deployment time**: 5-7 minutes

### Step 4: Update Auth0

After deployment completes, you'll see the service URL (e.g., `https://mdcalc-mcp-server-xxx.run.app`).

**IMPORTANT**: Update Auth0 API Identifier:
1. Go to [Auth0 Dashboard](https://manage.auth0.com/)
2. Navigate to: Applications → APIs → mdcalc-mcp-server
3. Update "Identifier" to your Cloud Run URL: `https://mdcalc-mcp-server-xxx.run.app`

### Step 5: Test Deployment

```bash
# Get service URL
SERVICE_URL=$(gcloud run services describe mdcalc-mcp-server \
  --region us-central1 \
  --format='value(status.url)')

echo $SERVICE_URL

# Test health endpoint
curl "$SERVICE_URL/health"

# Test OAuth metadata
curl "$SERVICE_URL/.well-known/oauth-protected-resource"
```

### Step 6: Add to Claude Android

1. Open Claude Android app
2. Go to Settings → Connectors
3. Add new MCP server with your Cloud Run URL
4. Server will auto-discover via DCR and authenticate

---

## Monitoring & Troubleshooting

### View Logs

```bash
# Tail logs in real-time
gcloud run services logs tail mdcalc-mcp-server \
  --region us-central1

# Search for specific patterns
gcloud run services logs tail mdcalc-mcp-server \
  --region us-central1 | grep -i "auth\|error\|blocked"
```

### Common Issues

#### 1. "Deployment configuration not found"

**Solution**:
```bash
cp .env.deployment.example .env.deployment
nano .env.deployment  # Fill in your values
```

#### 2. "Permission denied" for Secret Manager

**Cause**: Service account lacks permission

**Solution**:
```bash
PROJECT_NUMBER=$(gcloud projects describe YOUR_PROJECT_ID --format='value(projectNumber)')

gcloud secrets add-iam-policy-binding mdcalc-auth-state \
  --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor" \
  --project=YOUR_PROJECT_ID
```

#### 3. "No auth state found" in logs

**Cause**: Secret not mounted correctly

**Solution**:
```bash
# Verify secret exists
gcloud secrets describe mdcalc-auth-state

# Verify service has secret mounted
gcloud run services describe mdcalc-mcp-server \
  --region us-central1 \
  --format='yaml' | grep -A 5 secrets

# Re-deploy if needed
./scripts/deploy-to-cloud-run.sh
```

#### 4. MDCalc returns "Access Denied" errors

**Cause**: Session expired (happens every 30-90 days)

**Solution**: Refresh auth state (see Maintenance section below)

#### 5. "Invalid memory/CPU combination"

**Cause**: CPU exceeds memory limit

**Solution**: In `.env.deployment`, ensure CPU ≤ memory in Gi:
- Memory 1Gi → CPU ≤ 1
- Memory 2Gi → CPU ≤ 2
- Memory 4Gi → CPU ≤ 4

### Health Checks

**Success indicators in logs:**
```
✅ Loading auth state from Cloud Run secret
✅ Launched Chrome in headless mode
✅ Calculation complete
```

**Error indicators:**
```
❌ Access Denied
❌ MDCalc blocked request
❌ Bot detection triggered
→ Session likely expired, refresh required
```

---

## Maintenance

### Refresh Authentication State

MDCalc sessions expire every **30-90 days**. When you see "Access Denied" errors:

#### Option A: Automatic Script (Recommended)

```bash
# 1. Create new auth state
cd tools/recording-generator
python manual_login.py

# 2. Upload to Secret Manager
cd ../../mcp-servers/mdcalc-automation-mcp
./scripts/refresh-auth-state.sh
```

**No redeployment required!** Cloud Run automatically uses the latest secret version.

#### Option B: Manual Refresh

```bash
# 1. Create new auth state
cd tools/recording-generator
python manual_login.py

# 2. Update secret manually
gcloud secrets versions add mdcalc-auth-state \
  --data-file=../../recordings/auth/mdcalc_auth_state.json \
  --project=YOUR_PROJECT_ID
```

### Session Lifecycle

```
Day 0:   Create auth → Deploy                      ✅
Day 30:  Session valid                             ✅
Day 60:  Session valid                             ✅
Day 90:  Session expires                           ❌
         → Run manual_login.py
         → Run refresh-auth-state.sh
         → Session valid again                     ✅
```

### Monitoring Session Health

Set a calendar reminder to refresh every 60 days:

```bash
# Check for auth errors
gcloud run services logs tail mdcalc-mcp-server \
  --region us-central1 | grep -i "auth\|blocked\|denied"
```

### Update Deployment Configuration

If you need to change resources or other settings:

```bash
# 1. Edit .env.deployment
nano .env.deployment

# 2. Re-run deployment (preserves auth state)
./scripts/deploy-to-cloud-run.sh
```

---

## Security & Cost

### Security Best Practices

#### 1. Never Commit Secrets

`.env.deployment` is excluded from git via `.gitignore`:

```bash
# Verify
grep ".env.deployment" .gitignore
```

#### 2. Use Separate Projects for Dev/Prod

Create separate Google Cloud projects:
- `mdcalc-dev` - Development/testing
- `mdcalc-prod` - Production

Create separate `.env.deployment` files for each.

#### 3. Service Account Permissions

The deployment script grants **minimal permissions**:
- ✅ Read access to ONE specific secret (`mdcalc-auth-state`)
- ❌ NOT admin access
- ❌ NOT write access
- ❌ NOT delete access

#### 4. Monitor Secret Access

View who accessed the secret:

```bash
gcloud logging read \
  "resource.type=secret_manager_secret AND resource.labels.secret_id=mdcalc-auth-state" \
  --limit 50 \
  --format json
```

### Security Features

1. **Encrypted at rest**: Secret Manager encrypts all data
2. **Access controlled**: Only Cloud Run service account has access
3. **Not in Docker image**: Credentials never in container image
4. **Audited**: All access logged in Cloud Audit Logs
5. **Versioned**: Can rotate without redeployment

### Cost Estimation

**Monthly cost based on configuration:**

```
Configuration:
  Memory: 2Gi
  CPU: 2
  Min instances: 0 (scale to zero)
  Max instances: 10
  Timeout: 300s

Light usage (100 requests/day, 15s avg):
  Cloud Run: ~$2-5/month
  Secret Manager: $0 (free tier)
  Total: ~$2-5/month

Moderate usage (1000 requests/day, 15s avg):
  Cloud Run: ~$15-25/month
  Secret Manager: $0 (free tier)
  Total: ~$15-25/month

With MIN_INSTANCES=1 (always warm):
  Add ~$12/month for always-on instance
```

**Free tier:**
- Cloud Run: 2 million requests/month, 360,000 GB-seconds/month
- Secret Manager: 6 active secret versions, 10,000 access requests/month

**Recommendation**: Start with `MIN_INSTANCES=0` to minimize costs during testing.

---

## Summary

**Configuration files:**
- `.env.deployment.example` - Template (checked into git)
- `.env.deployment` - Your actual config (excluded from git)

**Service account:**
- Pre-existing Compute Engine default service account
- Format: `{PROJECT_NUMBER}-compute@developer.gserviceaccount.com`
- Granted minimal read permission to mdcalc-auth-state secret

**Deployment process:**
1. Create `.env.deployment` from template
2. Create MDCalc auth state with `manual_login.py`
3. Run `./scripts/deploy-to-cloud-run.sh`
4. Update Auth0 API Identifier with Cloud Run URL
5. Add to Claude Android

**Maintenance:**
- Refresh auth state every 30-90 days
- Monitor logs for errors
- Update configuration as needed

**Security:**
- All credentials encrypted and access-controlled
- No secrets in git or Docker images
- Full audit trail

**Cost:**
- ~$2-5/month for light usage
- Free tier covers most development/testing
