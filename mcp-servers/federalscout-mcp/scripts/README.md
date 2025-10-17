# FederalScout Demo Scripts

## start_browser_for_demo.py

Script to launch a pre-positioned browser for clean screen recordings.

### Why This Exists

When running FederalScout discovery in visible mode (for demos), the browser window needs to stay in a fixed position. This script launches a browser on a **predefined endpoint** that FederalScout can connect to, allowing you to position it exactly where you want before the demo starts.

### Usage

**Step 1: Configure .env file**

Add these lines to your `.env` file:

```bash
FEDERALSCOUT_BROWSER_ENDPOINT=http://localhost:9222
FEDERALSCOUT_BROWSER_TYPE=chromium
```

**Step 2: Launch the demo browser**

```bash
python scripts/start_browser_for_demo.py
```

This will:
- Launch Chromium with remote debugging on port 9222
- Open a blank page at 1000x1000 viewport
- Keep running in the foreground
- Print setup instructions

**Step 3: Position the browser**

Manually position the browser window exactly where you want it (e.g., right side of screen for split-screen recording).

**Step 4: Run your demo**

In another terminal, run either:

```bash
# Option A: Run pytest
pytest tests/test_session_persistence.py -v -s

# Option B: Start Claude Desktop
# FederalScout will connect to the existing browser
```

**Step 5: Stop the demo browser**

Press `Ctrl+C` in the terminal running `start_browser_for_demo.py` to close the browser.

### How It Works

1. The script launches Chrome/Chromium with `--remote-debugging-port=9222`
2. This exposes a remote debugging interface on `http://localhost:9222`
3. Playwright's `connect_over_cdp()` connects to this HTTP endpoint
4. Playwright auto-discovers the WebSocket endpoint from the HTTP interface
5. FederalScout uses the existing browser instead of launching a new one

### Benefits

- **Fixed window position**: Browser stays exactly where you positioned it
- **No copy/paste**: Predefined endpoint (`http://localhost:9222`) configured in .env
- **Clean recordings**: No window movement or jumping between monitors
- **Simple workflow**: Run script → position window → run tests/Claude Desktop

### Browser Requirements

The script looks for browsers in this order:

1. Google Chrome: `/Applications/Google Chrome.app/Contents/MacOS/Google Chrome`
2. Chromium: `/Applications/Chromium.app/Contents/MacOS/Chromium`

If neither is found, the script will error. Update the `chromium_path` variable in the script if your browser is in a different location.

### Troubleshooting

**"Failed to connect to existing browser"**
- Make sure the demo browser script is running
- Check that port 9222 is not already in use: `lsof -i :9222`
- Verify `.env` has correct endpoint: `FEDERALSCOUT_BROWSER_ENDPOINT=http://localhost:9222`

**"Chrome or Chromium not found"**
- Install Chrome or Chromium
- Or update the `chromium_path` in the script to match your installation

**Browser connects but wrong window**
- Make sure you positioned the browser window AFTER the script started
- The script opens `about:blank` - this is the window FederalScout will use
