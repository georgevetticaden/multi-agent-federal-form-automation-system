#!/bin/bash
# Deploy FederalRunner MCP Server to Google Cloud Run
# Includes wizards directory packaging from shared location

set -e  # Exit on error

echo "=================================================="
echo "FederalRunner MCP Server - Cloud Run Deployment"
echo "=================================================="

# Get script and project directories
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MCP_SERVER_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
PROJECT_ROOT="$(cd "$MCP_SERVER_DIR/../.." && pwd)"
DEPLOYMENT_ENV="$MCP_SERVER_DIR/.env.deployment"

echo ""
echo "Directories:"
echo "  MCP Server: $MCP_SERVER_DIR"
echo "  Project Root: $PROJECT_ROOT"
echo "  Wizards Source: $PROJECT_ROOT/wizards"

echo ""
echo "Loading deployment configuration..."
echo "-----------------------------------"

if [ ! -f "$DEPLOYMENT_ENV" ]; then
    echo "L ERROR: Deployment configuration not found!"
    echo ""
    echo "Please create .env.deployment file:"
    echo "  cd $MCP_SERVER_DIR"
    echo "  cp .env.deployment.example .env.deployment"
    echo "  nano .env.deployment  # Edit with your values"
    echo ""
    exit 1
fi

# Load environment variables from .env.deployment
set -a  # automatically export all variables
source "$DEPLOYMENT_ENV"
set +a

echo " Configuration loaded from: .env.deployment"

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
    echo "L ERROR: Missing required configuration variables:"
    printf '  - %s\n' "${missing_vars[@]}"
    echo ""
    echo "Please check your .env.deployment file"
    exit 1
fi

# Validate AUTH0_ISSUER has trailing slash
if [[ ! "$AUTH0_ISSUER" =~ /$ ]]; then
    echo "L ERROR: AUTH0_ISSUER must end with a trailing slash"
    echo "   Current: $AUTH0_ISSUER"
    echo "   Should be: ${AUTH0_ISSUER}/"
    exit 1
fi

# Validate CPU/Memory combination
MEMORY_GB="${MEMORY%Gi}"
if [ "$CPU" -gt "$MEMORY_GB" ]; then
    echo "L ERROR: CPU ($CPU) cannot exceed memory in Gi ($MEMORY_GB)"
    echo "   Valid combinations:"
    echo "     1Gi -> max 1 CPU"
    echo "     2Gi -> max 2 CPUs"
    echo "     4Gi -> max 4 CPUs"
    exit 1
fi

echo " Configuration validated"
echo ""
echo "Deployment Settings:"
echo "  Project ID: $PROJECT_ID"
echo "  Region: $REGION"
echo "  Service Name: $SERVICE_NAME"
echo "  Auth0 Domain: $AUTH0_DOMAIN"
echo "  Memory: $MEMORY"
echo "  CPU: $CPU"
echo "  Timeout: ${TIMEOUT}s"
echo "  Instances: $MIN_INSTANCES - $MAX_INSTANCES"

echo ""
echo "Step 1: Verify wizards directory exists"
echo "----------------------------------------"

WIZARDS_SOURCE="$PROJECT_ROOT/wizards"
if [ ! -d "$WIZARDS_SOURCE" ]; then
    echo "L ERROR: Wizards directory not found"
    echo ""
    echo "Expected location: $WIZARDS_SOURCE"
    echo ""
    echo "The wizards directory should contain:"
    echo "  - wizard-structures/  (discovered wizard data)"
    echo "  - data-schemas/       (user data schemas)"
    echo ""
    echo "Please run FederalScout to discover at least one wizard first."
    exit 1
fi

# Check for required subdirectories
if [ ! -d "$WIZARDS_SOURCE/wizard-structures" ]; then
    echo "L ERROR: wizard-structures directory not found in $WIZARDS_SOURCE"
    exit 1
fi

if [ ! -d "$WIZARDS_SOURCE/data-schemas" ]; then
    echo "L ERROR: data-schemas directory not found in $WIZARDS_SOURCE"
    exit 1
fi

# Count wizard files
WIZARD_COUNT=$(find "$WIZARDS_SOURCE/wizard-structures" -name "*.json" | wc -l | tr -d ' ')
SCHEMA_COUNT=$(find "$WIZARDS_SOURCE/data-schemas" -name "*.json" | wc -l | tr -d ' ')

if [ "$WIZARD_COUNT" -eq 0 ]; then
    echo "L ERROR: No wizard structure files found"
    echo "   Please run FederalScout to discover wizards first"
    exit 1
fi

if [ "$SCHEMA_COUNT" -eq 0 ]; then
    echo "L ERROR: No data schema files found"
    echo "   Please run FederalScout to generate schemas first"
    exit 1
fi

echo " Found wizards directory with:"
echo "   - $WIZARD_COUNT wizard structure(s)"
echo "   - $SCHEMA_COUNT data schema(s)"

echo ""
echo "Step 2: Copy wizards to build context"
echo "--------------------------------------"

# Clean up any existing wizards in build context
if [ -d "$MCP_SERVER_DIR/wizards" ]; then
    echo "Removing old wizards from build context..."
    rm -rf "$MCP_SERVER_DIR/wizards"
fi

# Copy wizards to build context (required by Dockerfile COPY command)
echo "Copying wizards: $WIZARDS_SOURCE -> $MCP_SERVER_DIR/wizards"
cp -r "$WIZARDS_SOURCE" "$MCP_SERVER_DIR/wizards"

# Verify copy succeeded
if [ ! -d "$MCP_SERVER_DIR/wizards/wizard-structures" ]; then
    echo "L ERROR: Failed to copy wizards directory"
    exit 1
fi

echo " Wizards copied to build context"

echo ""
echo "Step 3: Set Google Cloud project"
echo "---------------------------------"
gcloud config set project $PROJECT_ID
echo " Project set to: $PROJECT_ID"

echo ""
echo "Step 4: Verify billing is enabled"
echo "----------------------------------"
if ! gcloud billing projects describe $PROJECT_ID --format='value(billingEnabled)' 2>/dev/null | grep -q "True"; then
    echo "L ERROR: Billing is not enabled for project $PROJECT_ID"
    echo ""
    echo "Please enable billing:"
    echo "  https://console.cloud.google.com/billing/linkedaccount?project=$PROJECT_ID"
    exit 1
fi
echo " Billing is enabled"

echo ""
echo "Step 5: Enable required APIs"
echo "-----------------------------"
gcloud services enable run.googleapis.com
gcloud services enable cloudbuild.googleapis.com
echo " APIs enabled"

echo ""
echo "Step 6: Deploy to Cloud Run"
echo "----------------------------"
echo "This will take 3-5 minutes (building Docker image with WebKit)..."
echo ""
echo "Production Environment Variables:"
echo "  - Browser: webkit (headless mode compatible)"
echo "  - Headless: true (required for Cloud Run)"
echo "  - Save Screenshots: false (no disk persistence in production)"
echo "  - Execution Timeout: 180s (3 minutes for complete wizard execution)"
echo "  - Navigation Timeout: 120000ms (120s / 2 minutes - FSA can be VERY slow)"
echo "  - Cloud Run Request Timeout: ${TIMEOUT}s (allows execution to complete)"
echo "  - Wizards Dir: /app/wizards (from Docker image)"
echo ""
echo "Note: This will automatically create the Compute Engine default service account"
echo "      if it doesn't already exist in your project."
echo ""

# Deploy with placeholder environment variables (will be updated in Step 9)
# Capture the deployment output to extract the actual service URL
cd "$MCP_SERVER_DIR"

# Run deployment and capture output
DEPLOY_OUTPUT=$(gcloud run deploy $SERVICE_NAME \
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
    --set-env-vars="FEDERALRUNNER_BROWSER_TYPE=webkit" \
    --set-env-vars="FEDERALRUNNER_HEADLESS=true" \
    --set-env-vars="FEDERALRUNNER_SAVE_SCREENSHOTS=false" \
    --set-env-vars="FEDERALRUNNER_EXECUTION_TIMEOUT=180" \
    --set-env-vars="FEDERALRUNNER_NAVIGATION_TIMEOUT=120000" \
    --set-env-vars="FEDERALRUNNER_WIZARDS_DIR=/app/wizards" \
    --project=$PROJECT_ID 2>&1)

# Display the deployment output
echo "$DEPLOY_OUTPUT"

echo ""
echo "Step 7: Extract service URL from deployment output"
echo "---------------------------------------------------"

# Extract the service URL from the deployment output
# The deploy command outputs: "Service URL: https://..."
# Strip ANSI escape codes (color/formatting) from the URL
SERVICE_URL=$(echo "$DEPLOY_OUTPUT" | grep "Service URL:" | tail -1 | sed 's/Service URL: //' | sed 's/\x1b\[[0-9;]*m//g')

# Validate we got a URL
if [ -z "$SERVICE_URL" ]; then
    echo "ERROR: Could not extract service URL from deployment output"
    echo "Trying to get URL using gcloud describe..."
    SERVICE_URL=$(gcloud run services describe $SERVICE_NAME \
        --region $REGION \
        --project=$PROJECT_ID \
        --format='value(status.url)')
fi

echo " Service URL extracted: $SERVICE_URL"
echo ""

# Validate the URL matches the project-number format
# Expected format: https://SERVICE_NAME-PROJECT_NUMBER.REGION.run.app
if [[ ! "$SERVICE_URL" =~ -[0-9]+\. ]]; then
    echo "WARNING: Service URL does not match expected project-number format"
    echo "         Expected: https://$SERVICE_NAME-<PROJECT_NUMBER>.$REGION.run.app"
    echo "         Got:      $SERVICE_URL"
    echo ""
    echo "This may cause Auth0 audience validation to fail."
    echo "Please verify the URL in Google Cloud Console and update Auth0 accordingly."
    echo ""
fi

echo "Step 8: Update Auth0 API Audience"
echo "----------------------------------"
echo "IMPORTANT: You must update Auth0 with the deployed URL:"
echo ""
echo "  1. Go to: https://manage.auth0.com/dashboard/"
echo "  2. Navigate to: Applications -> APIs -> FederalRunner MCP Server"
echo "  3. Update Identifier to: $SERVICE_URL"
echo ""

echo "Step 9: Update Cloud Run environment variables"
echo "-----------------------------------------------"
echo "Updating AUTH0_API_AUDIENCE and MCP_SERVER_URL with real deployed URL..."
# Note: Must include ALL env vars when updating, not just the ones being changed
gcloud run services update $SERVICE_NAME \
    --region $REGION \
    --set-env-vars="AUTH0_DOMAIN=$AUTH0_DOMAIN,AUTH0_ISSUER=$AUTH0_ISSUER,AUTH0_API_AUDIENCE=$SERVICE_URL,MCP_SERVER_URL=$SERVICE_URL,FEDERALRUNNER_BROWSER_TYPE=webkit,FEDERALRUNNER_HEADLESS=true,FEDERALRUNNER_SAVE_SCREENSHOTS=false,FEDERALRUNNER_EXECUTION_TIMEOUT=180,FEDERALRUNNER_NAVIGATION_TIMEOUT=120000,FEDERALRUNNER_WIZARDS_DIR=/app/wizards" \
    --project=$PROJECT_ID
echo " Environment variables updated"

echo ""
echo "Step 10: Clean up build context"
echo "--------------------------------"

# Remove wizards from build context (no longer needed after deployment)
if [ -d "$MCP_SERVER_DIR/wizards" ]; then
    echo "Removing wizards from build context..."
    rm -rf "$MCP_SERVER_DIR/wizards"
    echo " Build context cleaned"
fi

echo ""
echo "Step 11: Test deployment"
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
    echo "�  Warning: Health check did not respond after $MAX_RETRIES attempts"
    echo "   Service may still be starting up. Check logs:"
    echo "   gcloud run services logs tail $SERVICE_NAME --region $REGION"
    echo ""
else
    echo ""
    echo "Testing OAuth metadata endpoint..."
    if oauth_response=$(curl -s -f "$SERVICE_URL/.well-known/oauth-protected-resource" 2>&1); then
        echo "$oauth_response" | jq .
    else
        echo "�  Warning: OAuth metadata endpoint not responding"
    fi
    echo ""
fi

echo "=================================================="
echo " DEPLOYMENT COMPLETE!"
echo "=================================================="
echo ""
echo "Next steps:"
echo "  1. Update Auth0 API Identifier to: $SERVICE_URL"
echo "  2. Enable Dynamic Client Registration (DCR) in Auth0"
echo "  3. Add connector in Claude.ai: Settings � Connectors"
echo "  4. Test in Claude web interface"
echo "  5. Verify sync to Claude Android (wait 2 minutes)"
echo ""
echo "Monitor & verify:"
echo "  # View logs in real-time"
echo "  gcloud run services logs tail $SERVICE_NAME --region $REGION"
echo ""
echo "  # Verify Playwright initialization (look for ' Playwright client initialized')"
echo "  gcloud run services logs tail $SERVICE_NAME --region $REGION | grep -i 'playwright'"
echo ""
echo "  # Check wizards loaded (look for wizard count)"
echo "  gcloud run services logs tail $SERVICE_NAME --region $REGION | grep -i 'wizard'"
echo ""
