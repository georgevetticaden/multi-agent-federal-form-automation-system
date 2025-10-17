#!/bin/bash
#
# Launch Chromium with CDP enabled for FederalScout demo mode
# This script launches Chromium with remote debugging on port 9222
# so that FederalScout can connect to it for clean screen recordings
#

echo "============================================================"
echo "     FederalScout Demo Browser Launcher"
echo "============================================================"
echo ""

# Kill any existing Chromium with debugging port
echo "🧹 Cleaning up any existing CDP browsers..."
pkill -f "remote-debugging-port=9222" 2>/dev/null

# Wait a moment for cleanup
sleep 1

# Check if Chromium/Chrome exists
CHROMIUM_PATH="/Applications/Chromium.app/Contents/MacOS/Chromium"
CHROME_PATH="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

if [ -f "$CHROMIUM_PATH" ]; then
    BROWSER_PATH="$CHROMIUM_PATH"
    BROWSER_NAME="Chromium"
elif [ -f "$CHROME_PATH" ]; then
    BROWSER_PATH="$CHROME_PATH"
    BROWSER_NAME="Chrome"
else
    echo "❌ Neither Chromium nor Chrome found!"
    echo "   Please install Chrome or Chromium"
    exit 1
fi

echo "🚀 Launching $BROWSER_NAME with CDP on port 9222..."
echo ""

# Create a temporary user data directory to ensure fresh instance
TEMP_DIR="/tmp/federalscout-chrome-demo-$$"
mkdir -p "$TEMP_DIR"

echo "📁 Using temporary profile: $TEMP_DIR"
echo ""

# Launch browser with CDP enabled and new profile
"$BROWSER_PATH" \
    --remote-debugging-port=9222 \
    --user-data-dir="$TEMP_DIR" \
    --no-first-run \
    --disable-default-apps \
    --disable-session-crashed-bubble \
    --disable-infobars \
    --window-size=1000,1000 \
    --new-window \
    about:blank &

BROWSER_PID=$!

# Wait for browser to start
sleep 2

# Check if CDP is accessible
MAX_ATTEMPTS=10
ATTEMPT=0
CDP_READY=false

echo "⏳ Waiting for CDP to be ready..."
while [ $ATTEMPT -lt $MAX_ATTEMPTS ]; do
    if curl -s http://127.0.0.1:9222/json/version > /dev/null 2>&1; then
        CDP_READY=true
        break
    fi
    sleep 1
    ATTEMPT=$((ATTEMPT + 1))
    echo -n "."
done
echo ""

if [ "$CDP_READY" = true ]; then
    echo "✅ Browser launched successfully!"
    echo ""
    echo "Browser Details:"
    echo "  - Type: $BROWSER_NAME"
    echo "  - Window size: 1000x1000"
    echo "  - CDP endpoint: http://127.0.0.1:9222"
    echo "  - Process ID: $BROWSER_PID"
    echo ""
    echo "============================================================"
    echo "📍 SETUP INSTRUCTIONS"
    echo "============================================================"
    echo ""
    echo "1. Position the browser window where you want it (right side of screen)"
    echo ""
    echo "2. Your .env file should have:"
    echo ""
    echo '   FEDERALSCOUT_BROWSER_ENDPOINT="http://127.0.0.1:9222"'
    echo '   FEDERALSCOUT_BROWSER_TYPE="chromium"'
    echo ""
    echo "3. Run pytest or start Claude Desktop"
    echo ""
    echo "4. FederalScout will connect to THIS browser (no window movement!)"
    echo ""
    echo "============================================================"
    echo ""
    echo "🛑 To stop the demo browser, run:"
    echo "   pkill -f 'remote-debugging-port=9222'"
    echo "   rm -rf $TEMP_DIR"
    echo ""
    echo "Press Ctrl+C to stop this script (browser will keep running)"
else
    echo "❌ CDP failed to start after $MAX_ATTEMPTS attempts"
    echo "   Try checking if port 9222 is already in use:"
    echo "   lsof -i :9222"
    exit 1
fi

echo ""
echo "============================================================"

# Keep script running to show it's active
echo "✅ Demo browser is ready! (Press Ctrl+C when done)"
echo ""

# Wait for user interrupt
trap "echo ''; echo '✅ Script stopped. Browser is still running.'; exit 0" INT
while true; do
    sleep 1
done
