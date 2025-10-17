# FederalRunner Cloud Run Deployment Requirements

**Version:** 1.0.0
**Status:** Design Approved
**Last Updated:** 2025-10-17

---

## Overview

This document defines the technical requirements for deploying FederalRunner Execution Agent to Google Cloud Run, including the critical path handling strategy that supports both local development (shared wizards directory) and Cloud Run deployment (packaged wizards).

**Key Constraint**: The `wizards/` directory is **SHARED** between FederalScout (writes) and FederalRunner (reads) in local development. This shared location must be preserved locally while supporting a different structure in Cloud Run.

---

## REQ-DEPLOY-001: Dual-Mode Path Configuration

### Requirement

FederalRunner MUST support two path resolution modes without code changes:

1. **Local Mode**: Shared wizards directory at project root
2. **Cloud Run Mode**: Packaged wizards inside Docker image

### Design Pattern

**Environment Variable Override Pattern** (same as MDCalc):

```python
# config.py __init__ method
if self.wizards_dir is None:
    # Pydantic will check FEDERALRUNNER_WIZARDS_DIR env var first
    # If not set, use local shared directory
    project_root = Path(__file__).parent.parent.parent.parent
    self.wizards_dir = project_root / "wizards"
```

**Local Development** (default):
```bash
# No env var set
# Result: /Users/aju/.../multi-agent-federal-form-automation-system/wizards/
```

**Cloud Run** (via env var):
```bash
# Set in deployment script
FEDERALRUNNER_WIZARDS_DIR=/app/wizards
# Result: /app/wizards/
```

### Directory Structure

**Local (Shared):**
```
multi-agent-federal-form-automation-system/
└── wizards/                              ← SHARED by both agents
    ├── wizard-structures/                ← FederalScout WRITES, FederalRunner READS
    │   └── fsa-estimator.json
    └── data-schemas/                     ← FederalScout WRITES, FederalRunner READS
        └── fsa-estimator-schema.json
```

**Cloud Run (Packaged):**
```
/app/
├── src/
│   ├── config.py
│   ├── execution_tools.py
│   └── server.py
└── wizards/                              ← Copied during deployment
    ├── wizard-structures/
    │   └── fsa-estimator.json
    └── data-schemas/
        └── fsa-estimator-schema.json
```

### Implementation Status

- ✅ Config supports environment variable override (`FEDERALRUNNER_WIZARDS_DIR`)
- ✅ Default path detection works for local development
- ✅ Comments document dual-mode design
- ⬜ Deployment script (Phase 5)
- ⬜ Dockerfile (Phase 5)

---

## REQ-DEPLOY-002: Dockerfile Specification

### Requirement

Dockerfile MUST:
1. Use Python 3.11+ base image
2. Install Playwright WebKit (FSA-compatible in headless mode)
3. Copy wizards directory into `/app/wizards/`
4. Verify wizard files are present before deployment
5. Set environment variables for production configuration

### Reference Implementation

See: `requirements/reference/mdcalc/Dockerfile` (lines 1-68)

**Key Differences from MDCalc:**

| Aspect | MDCalc | FederalRunner |
|--------|--------|---------------|
| Browser | Chromium | **WebKit** (FSA headless compatibility) |
| Data Location | `src/calculator-catalog/` (embedded) | `/app/wizards/` (copied at build time) |
| Data Pattern | Static catalog (never changes) | **Dynamic wizards** (updated by FederalScout) |
| Verification | `test -f mdcalc_catalog.json` | `test -d /app/wizards/wizard-structures && test -d /app/wizards/data-schemas` |

### Dockerfile Template (Phase 5)

```dockerfile
FROM python:3.11-slim

# Install Playwright system dependencies
RUN apt-get update && apt-get install -y \
    wget gnupg ca-certificates fonts-liberation \
    libasound2 libatk-bridge2.0-0 libatk1.0-0 \
    # ... (full list from MDCalc Dockerfile)
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright WebKit (NOT Chromium - FSA compatibility)
RUN playwright install webkit

# Copy application code
COPY src/ ./src/

# Copy wizards directory (from shared location)
COPY wizards/ ./wizards/

# Verify wizards are present
RUN test -d /app/wizards/wizard-structures || echo "ERROR: wizard-structures not found!"
RUN test -d /app/wizards/data-schemas || echo "ERROR: data-schemas not found!"
RUN ls -la /app/wizards/wizard-structures/ || exit 1
RUN ls -la /app/wizards/data-schemas/ || exit 1

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
ENV FEDERALRUNNER_WIZARDS_DIR=/app/wizards
ENV FEDERALRUNNER_BROWSER_TYPE=webkit
ENV FEDERALRUNNER_HEADLESS=true

EXPOSE 8080

CMD uvicorn src.server:app --host 0.0.0.0 --port ${PORT:-8080}
```

---

## REQ-DEPLOY-003: Deployment Script

### Requirement

Deployment script MUST:
1. Copy wizards from shared location to build context
2. Build Docker image with gcloud
3. Set environment variables for Cloud Run
4. Clean up copied wizards after deployment

### Deployment Script Template (Phase 5)

```bash
#!/bin/bash
# Deploy FederalRunner to Google Cloud Run

set -e  # Exit on error

echo "=================================================="
echo "FederalRunner - Cloud Run Deployment"
echo "=================================================="

# Step 1: Prepare build context
echo "Step 1: Copy wizards to build context"
echo "--------------------------------------"

# Copy shared wizards directory into mcp-servers/federalrunner-mcp/
# This makes it available to Docker COPY command
cp -r ../../wizards/ ./wizards/

echo "✅ Wizards copied to build context"

# Verify critical files exist
if [ ! -f ./wizards/wizard-structures/fsa-estimator.json ]; then
    echo "❌ ERROR: FSA wizard structure not found!"
    exit 1
fi

if [ ! -f ./wizards/data-schemas/fsa-estimator-schema.json ]; then
    echo "❌ ERROR: FSA wizard schema not found!"
    exit 1
fi

echo "✅ Wizard files verified"

# Step 2: Deploy to Cloud Run
echo ""
echo "Step 2: Deploy to Cloud Run"
echo "----------------------------"

gcloud run deploy federalrunner-mcp \
    --source . \
    --region $REGION \
    --allow-unauthenticated \
    --memory 2Gi \
    --cpu 2 \
    --timeout 60 \
    --set-env-vars="FEDERALRUNNER_BROWSER_TYPE=webkit" \
    --set-env-vars="FEDERALRUNNER_HEADLESS=true" \
    --set-env-vars="FEDERALRUNNER_WIZARDS_DIR=/app/wizards" \
    --set-env-vars="AUTH0_DOMAIN=$AUTH0_DOMAIN" \
    --set-env-vars="AUTH0_ISSUER=$AUTH0_ISSUER" \
    --project=$PROJECT_ID

# Step 3: Clean up build context
echo ""
echo "Step 3: Clean up build context"
echo "-------------------------------"

rm -rf ./wizards/

echo "✅ Build context cleaned"

echo ""
echo "=================================================="
echo "✅ DEPLOYMENT COMPLETE!"
echo "=================================================="
```

### Key Design Decision

**Why copy wizards at deployment time?**

1. ✅ **Preserves local shared directory** - FederalScout and FederalRunner continue to share `wizards/` locally
2. ✅ **Version control stays clean** - Don't duplicate wizards in two locations permanently
3. ✅ **Deployment uses latest data** - Always packages the current wizards discovered by FederalScout
4. ✅ **Matches MDCalc pattern** - MDCalc's calculator catalog is also static data packaged at build time

**Alternative considered and rejected:**
- ❌ Move wizards into `src/wizards/` permanently → Breaks FederalScout's write location
- ❌ Use Cloud Storage for wizards → Adds complexity, latency, and cost
- ❌ Mount Secret Manager for wizards → Secrets are for sensitive data, not static files

---

## REQ-DEPLOY-004: Browser Configuration

### Requirement

Cloud Run deployment MUST use WebKit browser in headless mode.

**Critical Constraint**: FSA website blocks headless Chromium and Firefox. Only WebKit works in headless mode with FSA.

### Configuration

| Environment | Browser | Headless | Rationale |
|-------------|---------|----------|-----------|
| **Local pytest Phase 1** | Chromium | ❌ False | Visual debugging |
| **Local pytest Phase 2** | WebKit | ✅ True | Production validation |
| **Local MCP Server** | Chromium | ❌ False | Interactive testing with Claude Desktop |
| **Cloud Run Production** | WebKit | ✅ True | FSA compatibility |

### Environment Variables

```bash
# Cloud Run deployment
FEDERALRUNNER_BROWSER_TYPE=webkit
FEDERALRUNNER_HEADLESS=true
FEDERALRUNNER_SLOW_MO=0
```

### Reference

See: `mcp-servers/federalrunner-mcp/src/config.py` lines 20-28 and 393-405

---

## REQ-DEPLOY-005: Resource Requirements

### Requirement

Cloud Run service MUST be configured with sufficient resources for Playwright execution.

### Specifications

```bash
--memory 2Gi           # Playwright + WebKit + DOM manipulation
--cpu 2                # Parallel field execution
--timeout 60           # Max 60 seconds per wizard execution
--min-instances 0      # Scale to zero when idle
--max-instances 10     # Handle concurrent requests
```

### Rationale

- **2Gi Memory**: Playwright browsers are memory-intensive
- **2 CPU**: Improves form execution speed
- **60s Timeout**: FSA wizard typically completes in 15-25 seconds, 60s provides buffer
- **Scale to zero**: Cost optimization (only pay for usage)

### Reference

See: `requirements/reference/mdcalc/mdcalc-deploy-to-cloud-run.sh` lines 55-59

---

## REQ-DEPLOY-006: Authentication

### Requirement

Cloud Run deployment MUST implement OAuth 2.1 authentication with Auth0.

### Implementation

Follow MDCalc authentication pattern:

1. **Auth0 API Configuration**
   - Create API resource in Auth0
   - Define scopes: `federalrunner:read`, `federalrunner:execute`
   - Configure API audience (Cloud Run URL)

2. **JWT Validation**
   - Validate tokens using JWKS (JSON Web Key Sets)
   - Require valid signature and claims
   - Enforce scope requirements per tool

3. **OAuth Metadata Endpoint**
   - Implement `/.well-known/oauth-protected-resource`
   - Return Auth0 issuer and authorization endpoint

### Reference

See:
- `requirements/shared/AUTHENTICATION_REQUIREMENTS.md`
- `requirements/reference/mdcalc/server.py` lines 1-750

---

## REQ-DEPLOY-007: Testing Strategy

### Requirement

Deployment process MUST include verification steps before and after deployment.

### Pre-Deployment Tests

```bash
# Run local tests (both phases)
cd mcp-servers/federalrunner-mcp
source venv/bin/activate
./run_tests.sh

# Verify all 6 tests pass
# - 2 MCP tool tests
# - 1 Phase 1 execution (non-headless)
# - 1 Phase 2 execution (headless WebKit)
# - 2 Error handling tests
```

### Post-Deployment Tests

```bash
# 1. Health check
curl https://federalrunner-mcp-xxx.run.app/health

# 2. OAuth metadata
curl https://federalrunner-mcp-xxx.run.app/.well-known/oauth-protected-resource

# 3. List wizards (requires auth token)
curl -H "Authorization: Bearer $TOKEN" \
     https://federalrunner-mcp-xxx.run.app/mcp/v1/tools/federalrunner_list_wizards

# 4. Execute wizard (requires auth token)
curl -X POST \
     -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"wizard_id":"fsa-estimator","user_data":{...}}' \
     https://federalrunner-mcp-xxx.run.app/mcp/v1/tools/federalrunner_execute_wizard
```

---

## Implementation Phases

### ✅ Phase 1-4: Local Development (COMPLETE)

- ✅ Playwright execution client
- ✅ Schema validator
- ✅ Execution tools (MCP)
- ✅ Local pytest tests
- ✅ Dual-mode path configuration (design)

### ⬜ Phase 5: Cloud Deployment (PENDING)

1. Create Dockerfile (REQ-DEPLOY-002)
2. Create deployment script (REQ-DEPLOY-003)
3. Configure Auth0 (REQ-DEPLOY-006)
4. Implement FastAPI server with OAuth 2.1
5. Deploy to Cloud Run
6. Post-deployment testing (REQ-DEPLOY-007)
7. Update `docs/deployment/DEPLOYMENT_GUIDE.md`

---

## References

- **MDCalc Deployment**: `requirements/reference/mdcalc/mdcalc-deploy-to-cloud-run.sh`
- **MDCalc Dockerfile**: `requirements/reference/mdcalc/Dockerfile`
- **Authentication**: `requirements/shared/AUTHENTICATION_REQUIREMENTS.md`
- **Local Config**: `mcp-servers/federalrunner-mcp/src/config.py`
- **Test Instructions**: `docs/execution/TEST_INSTRUCTIONS.md`

---

## Design Decisions

### Decision 1: Environment Variable Override Pattern

**Context**: Need to support both local (shared wizards) and Cloud Run (packaged wizards).

**Options Considered**:
1. Copy wizards into `src/wizards/` permanently
2. Use Cloud Storage for wizards
3. Environment variable override pattern (SELECTED)

**Decision**: Use environment variable override pattern because:
- ✅ Preserves local shared directory (FederalScout + FederalRunner)
- ✅ Matches MDCalc's proven pattern
- ✅ No code changes between environments
- ✅ Simple and maintainable

**Trade-offs**:
- Deployment script must copy wizards to build context
- Must remember to set `FEDERALRUNNER_WIZARDS_DIR` in Cloud Run

### Decision 2: WebKit Browser for Cloud Run

**Context**: FSA website blocks headless Chromium and Firefox.

**Decision**: Use WebKit browser in headless mode for Cloud Run.

**Evidence**: Two-phase testing approach validates this:
- Phase 1: Chromium non-headless (works)
- Phase 2: WebKit headless (works)
- ❌ Chromium headless (blocked by FSA)

**Impact**:
- ✅ Deployment works with FSA website
- ⚠️ Must install WebKit in Dockerfile (not Chromium)
- ✅ Same browser used in Phase 2 testing

---

## Status

**Current Status**: Design complete, ready for implementation in Phase 5

**Next Steps**:
1. Complete Phase 4 local testing
2. Begin Phase 5 when local tests pass
3. Implement Dockerfile and deployment script
4. Deploy to Cloud Run
5. Update deployment guide
