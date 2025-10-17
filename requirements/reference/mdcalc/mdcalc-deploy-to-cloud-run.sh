#!/bin/bash
# Deploy MDCalc MCP Server to Google Cloud Run with Secret Manager auth state

set -e  # Exit on error

echo "=================================================="
echo "MDCalc MCP Server - Cloud Run Deployment"
echo "=================================================="

# Load configuration from .env.deployment
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
DEPLOYMENT_ENV="$PROJECT_ROOT/.env.deployment"

echo ""
echo "Loading deployment configuration..."
echo "-----------------------------------"

if [ ! -f "$DEPLOYMENT_ENV" ]; then
    echo "❌ ERROR: Deployment configuration not found!"
    echo ""
    echo "Please create .env.deployment file:"
    echo "  cd $PROJECT_ROOT"
    echo "  cp .env.deployment.example .env.deployment"
    echo "  nano .env.deployment  # Edit with your values"
    echo ""
    exit 1
fi

# Load environment variables from .env.deployment
set -a  # automatically export all variables
source "$DEPLOYMENT_ENV"
set +a

echo "✅ Configuration loaded from: .env.deployment"

# Resolve auth state file path (relative to project root)
if [[ "$AUTH_STATE_FILE" == ../* ]]; then
    AUTH_STATE_FILE="$PROJECT_ROOT/$AUTH_STATE_FILE"
fi

echo ""
echo "Step 0: Validate configuration"
echo "-------------------------------"

# Required variables
required_vars=(
    "PROJECT_ID"
    "REGION"
    "SERVICE_NAME"
    "AUTH0_DOMAIN"
    "AUTH0_ISSUER"
    "SECRET_NAME"
    "AUTH_STATE_FILE"
    "MEMORY"
    "CPU"
    "TIMEOUT"
    "MIN_INSTANCES"
    "MAX_INSTANCES"
)

missing_vars=()
for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        missing_vars+=("$var")
    fi
done

if [ ${#missing_vars[@]} -gt 0 ]; then
    echo "❌ ERROR: Missing required configuration variables:"
    printf '  - %s\n' "${missing_vars[@]}"
    echo ""
    echo "Please check your .env.deployment file"
    exit 1
fi

# Validate AUTH0_ISSUER has trailing slash
if [[ ! "$AUTH0_ISSUER" =~ /$ ]]; then
    echo "❌ ERROR: AUTH0_ISSUER must end with a trailing slash"
    echo "   Current: $AUTH0_ISSUER"
    echo "   Should be: ${AUTH0_ISSUER}/"
    exit 1
fi

# Validate CPU/Memory combination
MEMORY_GB="${MEMORY%Gi}"
if [ "$CPU" -gt "$MEMORY_GB" ]; then
    echo "❌ ERROR: CPU ($CPU) cannot exceed memory in Gi ($MEMORY_GB)"
    echo "   Valid combinations:"
    echo "     1Gi → max 1 CPU"
    echo "     2Gi → max 2 CPUs"
    echo "     4Gi → max 4 CPUs"
    exit 1
fi

echo "✅ Configuration validated"
echo ""
echo "Deployment Settings:"
echo "  Project ID: $PROJECT_ID"
echo "  Region: $REGION"
echo "  Service Name: $SERVICE_NAME"
echo "  Auth0 Domain: $AUTH0_DOMAIN"
echo "  Secret Name: $SECRET_NAME"
echo "  Memory: $MEMORY"
echo "  CPU: $CPU"
echo "  Timeout: ${TIMEOUT}s"
echo "  Instances: $MIN_INSTANCES - $MAX_INSTANCES"

echo ""
echo "Step 1: Verify auth state file exists"
echo "--------------------------------------"

if [ ! -f "$AUTH_STATE_FILE" ]; then
    echo "❌ ERROR: Auth state file not found"
    echo ""
    echo "Expected location: $AUTH_STATE_FILE"
    echo ""
    echo "To create the auth state file:"
    echo "  1. cd tools/recording-generator"
    echo "  2. python manual_login.py"
    echo "  3. This will create: recordings/auth/mdcalc_auth_state.json"
    echo ""
    echo "The file contains MDCalc session cookies and must be created"
    echo "through manual login to bypass bot detection."
    exit 1
fi

# Validate it's valid JSON
if ! python3 -c "import json; json.load(open('$AUTH_STATE_FILE'))" 2>/dev/null; then
    echo "❌ ERROR: Auth state file is not valid JSON"
    echo ""
    echo "File: $AUTH_STATE_FILE"
    echo ""
    echo "Please recreate the auth state:"
    echo "  cd tools/recording-generator"
    echo "  python manual_login.py"
    exit 13
fi

echo "✅ Found valid auth state file: $AUTH_STATE_FILE"

echo ""
echo "Step 2: Set Google Cloud project"
echo "---------------------------------"
gcloud config set project $PROJECT_ID
echo "✅ Project set to: $PROJECT_ID"

echo ""
echo "Step 3: Verify billing is enabled"
echo "----------------------------------"
if ! gcloud billing projects describe $PROJECT_ID --format='value(billingEnabled)' 2>/dev/null | grep -q "True"; then
    echo "❌ ERROR: Billing is not enabled for project $PROJECT_ID"
    echo ""
    echo "Please enable billing:"
    echo "  https://console.cloud.google.com/billing/linkedaccount?project=$PROJECT_ID"
    exit 1
fi
echo "✅ Billing is enabled"

echo ""
echo "Step 4: Enable required APIs"
echo "-----------------------------"
gcloud services enable run.googleapis.com
gcloud services enable secretmanager.googleapis.com
gcloud services enable cloudbuild.googleapis.com
echo "✅ APIs enabled"

echo ""
echo "Step 5: Create or update Secret Manager secret"
echo "-----------------------------------------------"

# Check if secret exists
if gcloud secrets describe $SECRET_NAME --project=$PROJECT_ID &>/dev/null; then
    echo "Secret exists, adding new version..."
    gcloud secrets versions add $SECRET_NAME \
        --data-file="$AUTH_STATE_FILE" \
        --project=$PROJECT_ID
else
    echo "Creating new secret..."
    gcloud secrets create $SECRET_NAME \
        --data-file="$AUTH_STATE_FILE" \
        --replication-policy="automatic" \
        --project=$PROJECT_ID
fi
echo "✅ Secret created/updated: $SECRET_NAME"

echo ""
echo "Step 6: Deploy to Cloud Run"
echo "----------------------------"
echo "This will take 3-5 minutes..."
echo ""
echo "Note: This will automatically create the Compute Engine default service account"
echo "      if it doesn't already exist in your project."
echo ""

# Deploy with secret mounted (without secret initially - will update after permissions)
# NOTE: We can't mount the secret yet because the service account doesn't have permission
# We'll deploy first, grant permissions, then update the service to mount the secret
# Set temporary placeholders for AUTH0_API_AUDIENCE and MCP_SERVER_URL (will be updated in Step 12)
gcloud run deploy $SERVICE_NAME \
    --source . \
    --region $REGION \
    --allow-unauthenticated \
    --memory $MEMORY \
    --cpu $CPU \
    --timeout $TIMEOUT \
    --min-instances $MIN_INSTANCES \
    --max-instances $MAX_INSTANCES \
    --set-env-vars="AUTH0_DOMAIN=$AUTH0_DOMAIN" \
    --set-env-vars="AUTH0_ISSUER=$AUTH0_ISSUER" \
    --set-env-vars="AUTH0_API_AUDIENCE=https://placeholder-will-be-updated.run.app" \
    --set-env-vars="MCP_SERVER_URL=https://placeholder-will-be-updated.run.app" \
    --project=$PROJECT_ID

echo ""
echo "Step 7: Get Cloud Run service account"
echo "--------------------------------------"
echo "The deployment created the service account. Getting details..."
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format='value(projectNumber)')
SERVICE_ACCOUNT="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"
echo "Service account: $SERVICE_ACCOUNT"

# Verify it exists
if gcloud iam service-accounts describe $SERVICE_ACCOUNT --project=$PROJECT_ID &>/dev/null; then
    echo "✅ Service account verified"
else
    echo "❌ ERROR: Service account was not created by Cloud Run deployment"
    echo "   This is unexpected. Please check Cloud Run deployment logs."
    exit 1
fi

echo ""
echo "Step 8: Grant secret access to Cloud Run service account"
echo "---------------------------------------------------------"
gcloud secrets add-iam-policy-binding $SECRET_NAME \
    --member="serviceAccount:$SERVICE_ACCOUNT" \
    --role="roles/secretmanager.secretAccessor" \
    --project=$PROJECT_ID
echo "✅ Permissions granted"

echo ""
echo "Step 9: Update Cloud Run to mount secret"
echo "-----------------------------------------"
echo "Now that permissions are granted, mounting the auth state secret..."
gcloud run services update $SERVICE_NAME \
    --region $REGION \
    --set-secrets="/app/auth/mdcalc_auth_state.json=$SECRET_NAME:latest" \
    --project=$PROJECT_ID
echo "✅ Secret mounted"

echo ""
echo "Step 10: Get service URL"
echo "------------------------"
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME \
    --region $REGION \
    --project=$PROJECT_ID \
    --format='value(status.url)')

echo "✅ Service deployed!"
echo ""
echo "Service URL: $SERVICE_URL"
echo ""

echo "Step 11: Update Auth0 API Audience"
echo "-----------------------------------"
echo "IMPORTANT: You must update Auth0 with the deployed URL:"
echo ""
echo "  1. Go to: https://manage.auth0.com/dashboard/"
echo "  2. Navigate to: Applications → APIs → mdcalc-mcp-server"
echo "  3. Update Identifier to: $SERVICE_URL"
echo ""

echo "Step 12: Update Cloud Run environment variables"
echo "------------------------------------------------"
echo "Updating AUTH0_API_AUDIENCE and MCP_SERVER_URL with real deployed URL..."
# Note: Must include ALL env vars when updating, not just the ones being changed
gcloud run services update $SERVICE_NAME \
    --region $REGION \
    --set-env-vars="AUTH0_DOMAIN=$AUTH0_DOMAIN,AUTH0_ISSUER=$AUTH0_ISSUER,AUTH0_API_AUDIENCE=$SERVICE_URL,MCP_SERVER_URL=$SERVICE_URL" \
    --project=$PROJECT_ID
echo "✅ Environment variables updated"

echo ""
echo "Step 13: Test deployment"
echo "------------------------"

# Test health endpoint with retries
echo "Testing health endpoint..."
MAX_RETRIES=20  # 20 retries * 3 seconds = 60 seconds total
RETRY_COUNT=0
HEALTH_OK=false

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if response=$(curl -s -f "$SERVICE_URL/health" 2>&1); then
        echo "$response" | jq .
        HEALTH_OK=true
        break
    fi
    RETRY_COUNT=$((RETRY_COUNT + 1))
    echo "Waiting for service to be ready... ($RETRY_COUNT/$MAX_RETRIES)"
    sleep 3
done

if [ "$HEALTH_OK" = false ]; then
    echo "⚠️  Warning: Health check did not respond after $MAX_RETRIES attempts"
    echo "   Service may still be starting up. Check logs:"
    echo "   gcloud run services logs tail $SERVICE_NAME --region $REGION"
    echo ""
else
    echo ""
    echo "Testing OAuth metadata endpoint..."
    if oauth_response=$(curl -s -f "$SERVICE_URL/.well-known/oauth-protected-resource" 2>&1); then
        echo "$oauth_response" | jq .
    else
        echo "⚠️  Warning: OAuth metadata endpoint not responding"
    fi
    echo ""
fi

echo "=================================================="
echo "✅ DEPLOYMENT COMPLETE!"
echo "=================================================="
echo ""
echo "Next steps:"
echo "  1. Update Auth0 API Identifier to: $SERVICE_URL"
echo "  2. Add connector in Claude.ai: Settings → Connectors"
echo "  3. Test in Claude web interface"
echo "  4. Verify sync to Claude Android (wait 2 minutes)"
echo ""
echo "Monitor & verify:"
echo "  # View logs in real-time"
echo "  gcloud run services logs tail $SERVICE_NAME --region $REGION"
echo ""
echo "  # Verify auth state loaded (look for '✅ Loading auth state from Cloud Run secret')"
echo "  gcloud run services logs tail $SERVICE_NAME --region $REGION | grep -i 'auth state'"
echo ""
