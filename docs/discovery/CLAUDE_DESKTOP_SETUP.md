# FederalScout - Claude Desktop Setup Guide

Complete guide to configuring FederalScout MCP server in Claude Desktop for interactive wizard discovery.

---

## Prerequisites

1. **Claude Desktop app** installed
2. **Python 3.11+** installed
3. **FederalScout dependencies** installed (see [Quick Start](#quick-start))

---

## Quick Start

```bash
# 1. Navigate to FederalScout directory
cd mcp-servers/federalscout-mcp

# 2. Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Install Playwright browsers
playwright install webkit chromium
```

---

## Configuration

### Configuration File Location

Claude Desktop MCP configuration file:
```
~/Library/Application Support/Claude/claude_desktop_config.json
```

### Configuration Structure

FederalScout requires the following configuration structure:

```json
{
  "mcpServers": {
    "federalscout": {
      "command": "<absolute-path-to-venv-python>",
      "args": ["<absolute-path-to-server.py>"],
      "env": {
        // Browser settings
        "FEDERALSCOUT_BROWSER_TYPE": "webkit|chromium",
        "FEDERALSCOUT_HEADLESS": "false",
        "FEDERALSCOUT_SLOW_MO": "500",

        // Viewport settings
        "FEDERALSCOUT_VIEWPORT_WIDTH": "1000",
        "FEDERALSCOUT_VIEWPORT_HEIGHT": "1000",

        // Screenshot settings
        "FEDERALSCOUT_SCREENSHOT_QUALITY": "60",
        "FEDERALSCOUT_SCREENSHOT_MAX_SIZE_KB": "50",
        "FEDERALSCOUT_SAVE_SCREENSHOTS": "true",

        // Session settings
        "FEDERALSCOUT_SESSION_TIMEOUT": "1800",

        // Directory settings (REQUIRED for Claude Desktop)
        "FEDERALSCOUT_WORKSPACE_ROOT": "<absolute-path-to-federalscout-mcp>",
        "FEDERALSCOUT_WIZARDS_DIR": "<absolute-path-to-formflow-agent>/wizards",
        "FEDERALSCOUT_LOG_DIR": "<absolute-path-to-federalscout-mcp>/logs",
        "FEDERALSCOUT_SCREENSHOT_DIR": "<absolute-path-to-federalscout-mcp>/screenshots",

        // Demo mode (optional - for screen recording)
        "FEDERALSCOUT_BROWSER_ENDPOINT": "http://127.0.0.1:9222"
      }
    }
  }
}
```

---

## Configuration Examples

### Example 1: Standard Mode (Recommended for Testing)

**Use case:** Normal discovery workflow with new browser each session

```json
{
  "mcpServers": {
    "federalscout": {
      "command": "/absolute/path/to/formflow-agent/mcp-servers/federalscout-mcp/venv/bin/python",
      "args": [
        "/absolute/path/to/formflow-agent/mcp-servers/federalscout-mcp/src/server.py"
      ],
      "env": {
        "FEDERALSCOUT_BROWSER_TYPE": "webkit",
        "FEDERALSCOUT_HEADLESS": "false",
        "FEDERALSCOUT_SLOW_MO": "500",
        "FEDERALSCOUT_VIEWPORT_WIDTH": "1000",
        "FEDERALSCOUT_VIEWPORT_HEIGHT": "1000",
        "FEDERALSCOUT_SCREENSHOT_QUALITY": "60",
        "FEDERALSCOUT_SCREENSHOT_MAX_SIZE_KB": "50",
        "FEDERALSCOUT_SAVE_SCREENSHOTS": "true",
        "FEDERALSCOUT_SESSION_TIMEOUT": "1800",
        "FEDERALSCOUT_WORKSPACE_ROOT": "/absolute/path/to/formflow-agent/mcp-servers/federalscout-mcp",
        "FEDERALSCOUT_WIZARDS_DIR": "/absolute/path/to/formflow-agent/wizards",
        "FEDERALSCOUT_LOG_DIR": "/absolute/path/to/formflow-agent/mcp-servers/federalscout-mcp/logs",
        "FEDERALSCOUT_SCREENSHOT_DIR": "/absolute/path/to/formflow-agent/wizards/screenshots/form-scout"
      }
    }
  }
}
```

**Key features:**
- ✅ Uses WebKit (best compatibility with government sites)
- ✅ Launches new browser for each discovery session
- ✅ Browser visible (not headless) for debugging
- ✅ 1000x1000 viewport for split-screen layout

---

### Example 2: Demo Mode (Screen Recording)

**Use case:** Pre-positioned browser for clean screen recordings

```json
{
  "mcpServers": {
    "federalscout": {
      "command": "/Users/aju/Dropbox/Development/Git/10-14-25-gov-formflow-agent/formflow-agent/mcp-servers/federalscout-mcp/venv/bin/python",
      "args": [
        "/Users/aju/Dropbox/Development/Git/10-14-25-gov-formflow-agent/formflow-agent/mcp-servers/federalscout-mcp/src/server.py"
      ],
      "env": {
        "FEDERALSCOUT_BROWSER_ENDPOINT": "http://127.0.0.1:9222",
        "FEDERALSCOUT_BROWSER_TYPE": "chromium",
        "FEDERALSCOUT_HEADLESS": "false",
        "FEDERALSCOUT_SLOW_MO": "500",
        "FEDERALSCOUT_VIEWPORT_WIDTH": "1000",
        "FEDERALSCOUT_VIEWPORT_HEIGHT": "1000",
        "FEDERALSCOUT_SCREENSHOT_QUALITY": "60",
        "FEDERALSCOUT_SCREENSHOT_MAX_SIZE_KB": "50",
        "FEDERALSCOUT_SAVE_SCREENSHOTS": "true",
        "FEDERALSCOUT_SESSION_TIMEOUT": "1800",
        "FEDERALSCOUT_WORKSPACE_ROOT": "/Users/aju/Dropbox/Development/Git/10-14-25-gov-formflow-agent/formflow-agent/mcp-servers/federalscout-mcp",
        "FEDERALSCOUT_WIZARDS_DIR": "/Users/aju/Dropbox/Development/Git/10-14-25-gov-formflow-agent/formflow-agent/wizards",
        "FEDERALSCOUT_LOG_DIR": "/Users/aju/Dropbox/Development/Git/10-14-25-gov-formflow-agent/formflow-agent/mcp-servers/federalscout-mcp/logs",
        "FEDERALSCOUT_SCREENSHOT_DIR": "/Users/aju/Dropbox/Development/Git/10-14-25-gov-formflow-agent/formflow-agent/wizards/screenshots/form-scout"
      }
    }
  }
}
```

**Key features:**
- ✅ Connects to pre-positioned browser (no window movement!)
- ✅ Uses Chromium with Chrome DevTools Protocol (CDP)
- ✅ Fixed 1000x1000 viewport throughout session
- ✅ Perfect for split-screen recording (Claude Desktop left, Browser right)

**How to use demo mode:**

1. **Start the demo browser:**
   ```bash
   cd /Users/aju/Dropbox/Development/Git/10-14-25-gov-formflow-agent/formflow-agent/mcp-servers/federalscout-mcp
   bash scripts/start_browser_for_demo.sh
   ```

2. **Position browser window:**
   - Move browser to right side of screen
   - Adjust size/position for your recording layout
   - Leave browser running

3. **Start Claude Desktop:**
   - FederalScout will connect to existing browser
   - Browser stays exactly where you positioned it
   - No window resizing or movement during discovery

4. **Important notes:**
   - ⚠️ Use `http://127.0.0.1:9222` (not `localhost`) to avoid IPv6 issues on macOS
   - ⚠️ Must use `chromium` browser type with demo mode
   - ⚠️ Browser window stays fixed at 1000x1000 (aggressive zoom fits content)

---

## Environment Variable Reference

### Browser Settings

| Variable | Values | Default | Description |
|----------|--------|---------|-------------|
| `FEDERALSCOUT_BROWSER_TYPE` | `webkit`, `chromium`, `firefox` | `webkit` | Browser engine to use. **WebKit recommended** for government sites with bot detection |
| `FEDERALSCOUT_HEADLESS` | `true`, `false` | `false` | Run browser in headless mode. Set to `false` for testing/recording |
| `FEDERALSCOUT_SLOW_MO` | `0-5000` (ms) | `500` | Slow down browser actions (helpful for watching discovery) |

### Viewport Settings

| Variable | Values | Default | Description |
|----------|--------|---------|-------------|
| `FEDERALSCOUT_VIEWPORT_WIDTH` | pixels | `1000` | Browser viewport width |
| `FEDERALSCOUT_VIEWPORT_HEIGHT` | pixels | `1000` | Browser viewport height |

**Viewport recommendations:**
- **Split-screen recording:** 1000×1000 (Claude Desktop left, Browser right)
- **Full-screen browser:** 1200×1400 or larger
- **Taller viewport:** 1000×1400 (fits more form fields)

**How viewport works:**
- Window stays **fixed** at configured size (no resizing!)
- Content **zooms aggressively** (20-100%) to fit in fixed viewport
- Example: 2224px FSA form zooms to ~44%, fits in 1000px viewport
- Result: Complete form capture in fixed window, perfect for recording

### Screenshot Settings

| Variable | Values | Default | Description |
|----------|--------|---------|-------------|
| `FEDERALSCOUT_SCREENSHOT_QUALITY` | `1-100` | `60` | JPEG quality (60 = ~50KB per image) |
| `FEDERALSCOUT_SCREENSHOT_MAX_SIZE_KB` | KB | `50` | Target max screenshot size |
| `FEDERALSCOUT_SAVE_SCREENSHOTS` | `true`, `false` | `true` | Save screenshots to disk for debugging |

### Session Settings

| Variable | Values | Default | Description |
|----------|--------|---------|-------------|
| `FEDERALSCOUT_SESSION_TIMEOUT` | seconds | `1800` | Session timeout (1800 = 30 minutes) |

### Directory Settings (REQUIRED for Claude Desktop)

| Variable | Description | Example |
|----------|-------------|---------|
| `FEDERALSCOUT_WORKSPACE_ROOT` | FederalScout project root | `/path/to/federalscout-mcp` |
| `FEDERALSCOUT_WIZARDS_DIR` | **Shared wizards directory** (formflow-agent/wizards) | `/path/to/formflow-agent/wizards` |
| `FEDERALSCOUT_LOG_DIR` | FederalScout application logs | `/path/to/federalscout-mcp/logs` |
| `FEDERALSCOUT_SCREENSHOT_DIR` | **Shared screenshots directory** | `/path/to/formflow-agent/wizards/screenshots/form-scout` |

**Important directory structure:**
```
formflow-agent/
├── wizards/                          # SHARED wizard directory
│   ├── data-schemas/                 # User Data Schemas (Contract)
│   │   └── fsa-estimator-schema.json
│   ├── wizard-structures/            # Wizard Structures (Playwright instructions)
│   │   └── fsa-estimator.json
│   └── screenshots/                  # SHARED screenshots directory
│       └── form-scout/               # FederalScout discovery screenshots
│           └── screenshot_*.jpg
│
└── mcp-servers/
    ├── federalscout-mcp/                # FederalScout (Discovery)
    │   └── logs/                     # FederalScout logs
    │
    └── federalrunner-mcp/                # FederalRunner (Execution)
        └── logs/                     # FederalRunner logs
```

**Why shared directories:**
- FederalScout discovers wizard structures → saves to `formflow-agent/wizards/wizard-structures/`
- FederalScout saves screenshots → saves to `formflow-agent/wizards/screenshots/form-scout/`
- FederalRunner reads wizard structures ← loads from `formflow-agent/wizards/wizard-structures/`
- All wizards and discovery artifacts in one shared location
- Version controlled in git at project root level

### Demo Mode Settings (Optional)

| Variable | Values | Description |
|----------|--------|-------------|
| `FEDERALSCOUT_BROWSER_ENDPOINT` | `http://127.0.0.1:9222` | Connect to existing browser via CDP. **Use 127.0.0.1 not localhost** (IPv6 issues) |

**When to use demo mode:**
- Screen recording wizard discovery
- Need browser in exact position
- Want fixed window size throughout session
- Recording split-screen layout (Claude Desktop + Browser)

---

## Setup Steps

### 1. Edit Claude Desktop Config

```bash
# Open config file in editor
open ~/Library/Application\ Support/Claude/claude_desktop_config.json
```

Or use any text editor:
```bash
nano ~/Library/Application\ Support/Claude/claude_desktop_config.json
```

### 2. Add FederalScout Configuration

Copy one of the examples above and **replace all placeholder paths** with your actual paths:
- Replace `/absolute/path/to/` with your actual project path
- Use **absolute paths** (not relative)
- Use the **venv Python** (in `venv/bin/python`)

### 3. Verify Paths

Make sure all paths exist:
```bash
# Check venv Python exists
ls -la /Users/aju/Dropbox/Development/Git/10-14-25-gov-formflow-agent/formflow-agent/mcp-servers/federalscout-mcp/venv/bin/python

# Check server.py exists
ls -la /Users/aju/Dropbox/Development/Git/10-14-25-gov-formflow-agent/formflow-agent/mcp-servers/federalscout-mcp/src/server.py

# Check wizards directory exists
ls -la /Users/aju/Dropbox/Development/Git/10-14-25-gov-formflow-agent/formflow-agent/wizards
```

### 4. Restart Claude Desktop

1. **Quit completely:** Cmd+Q (don't just close window)
2. **Reopen** Claude Desktop
3. **Verify connection:** Settings → Developer → MCP Servers
4. **Check status:** "federalscout" should show as "Connected"

---

## Testing

### 1. Verify Server Connection

In Claude Desktop Settings:
- Go to **Settings → Developer → MCP Servers**
- Look for **"federalscout"** in the list
- Status should show **"Connected"** with green indicator
- If not connected, check logs (see Troubleshooting)

### 2. Test Discovery

Start a conversation in Claude Desktop:

```
Discover the FSA Student Aid Estimator wizard at https://studentaid.gov/aid-estimator/
```

**Expected behavior:**
1. Claude calls `federalscout_start_discovery` tool
2. Browser window opens (WebKit or Chromium)
3. Browser navigates to FSA website
4. Claude receives screenshot
5. Claude analyzes page and continues discovery
6. Progress saved incrementally to `wizards/` directory

### 3. Monitor Logs

Watch logs in real-time:
```bash
tail -f /Users/aju/Dropbox/Development/Git/10-14-25-gov-formflow-agent/formflow-agent/mcp-servers/federalscout-mcp/logs/federalscout.log
```

**What to look for:**
- ✅ `Starting FederalScout MCP server (stdio)`
- ✅ `MCP tool called: federalscout_start_discovery`
- ✅ `🆕 NEW SESSION: <session-id>`
- ✅ `📸 Screenshot: screenshot_*.jpg`
- ✅ `✅ DISCOVERY COMPLETE!`

### 4. Check Output

After discovery completes:
```bash
# Check wizard structure was created
ls -la ~/Dropbox/Development/Git/10-14-25-gov-formflow-agent/formflow-agent/wizards/wizard-structures/

# Check screenshots were saved
ls -la ~/Dropbox/Development/Git/10-14-25-gov-formflow-agent/formflow-agent/wizards/screenshots/form-scout/

# View wizard JSON
cat ~/Dropbox/Development/Git/10-14-25-gov-formflow-agent/formflow-agent/wizards/wizard-structures/fsa-estimator.json | jq
```

---

## Troubleshooting

### Server Not Connected

**Symptom:** FederalScout shows "Disconnected" in Claude Desktop settings

**Fixes:**
1. Check Python path is absolute and points to venv Python
2. Check server.py path is absolute
3. Verify venv has all dependencies: `pip list | grep mcp`
4. Check Claude Desktop logs:
   ```bash
   tail -f ~/Library/Logs/Claude/mcp*.log
   ```

### Browser Doesn't Open

**Symptom:** Tool call succeeds but no browser window appears

**Fixes:**
1. Check `FEDERALSCOUT_HEADLESS=false` in config
2. Verify Playwright browser installed:
   ```bash
   playwright install webkit
   ```
3. Try different browser type: `chromium` instead of `webkit`

### Screenshots Not Saving

**Symptom:** No screenshots in screenshots directory

**Fixes:**
1. Check `FEDERALSCOUT_SAVE_SCREENSHOTS=true` in config
2. Verify screenshot directory exists and is writable:
   ```bash
   mkdir -p /path/to/formflow-agent/wizards/screenshots/form-scout
   chmod 755 /path/to/formflow-agent/wizards/screenshots/form-scout
   ```
3. Check disk space: `df -h`

### Demo Mode Connection Refused

**Symptom:** Error: `connect ECONNREFUSED 127.0.0.1:9222`

**Fixes:**
1. Verify demo browser is running:
   ```bash
   curl http://127.0.0.1:9222/json/version
   ```
2. Kill any existing CDP browsers:
   ```bash
   pkill -f "remote-debugging-port=9222"
   ```
3. Restart demo browser:
   ```bash
   bash scripts/start_browser_for_demo.sh
   ```
4. Use `127.0.0.1` not `localhost` (IPv6 issues on macOS)

### Session Timeout Errors

**Symptom:** Error: "Session expired"

**Fixes:**
1. Increase timeout: `FEDERALSCOUT_SESSION_TIMEOUT=3600` (60 minutes)
2. Complete discovery faster (use batch actions)
3. Start new discovery session

### Directory Not Found Errors

**Symptom:** Error: "No such file or directory: /path/to/wizards"

**Fixes:**
1. Create missing directories:
   ```bash
   mkdir -p /path/to/formflow-agent/wizards/wizard-structures
   mkdir -p /path/to/formflow-agent/wizards/data-schemas
   mkdir -p /path/to/formflow-agent/wizards/screenshots/form-scout
   mkdir -p /path/to/federalscout-mcp/logs
   ```
2. Check all paths in config are **absolute** (not relative)
3. Verify paths are correct (no typos)

---

## Advanced Configuration

### Multiple Viewport Configurations

You can create multiple FederalScout configurations for different use cases:

```json
{
  "mcpServers": {
    "federalscout-demo": {
      "command": "/path/to/venv/bin/python",
      "args": ["/path/to/src/server.py"],
      "env": {
        "FEDERALSCOUT_BROWSER_ENDPOINT": "http://127.0.0.1:9222",
        "FEDERALSCOUT_BROWSER_TYPE": "chromium",
        "FEDERALSCOUT_VIEWPORT_WIDTH": "1000",
        "FEDERALSCOUT_VIEWPORT_HEIGHT": "1000"
      }
    },
    "federalscout-fullscreen": {
      "command": "/path/to/venv/bin/python",
      "args": ["/path/to/src/server.py"],
      "env": {
        "FEDERALSCOUT_BROWSER_TYPE": "webkit",
        "FEDERALSCOUT_VIEWPORT_WIDTH": "1600",
        "FEDERALSCOUT_VIEWPORT_HEIGHT": "1400"
      }
    }
  }
}
```

This allows you to switch between configurations without editing the config file.

---

## Next Steps

Once FederalScout is working in Claude Desktop:

1. ✅ **Discover FSA Estimator** - Test with known working wizard
2. ✅ **Review wizard JSON** - Verify structure is complete
3. ✅ **Generate data schema** - Use `federalscout_save_schema` tool
4. ✅ **Test other wizards** - SSA, IRS calculators, etc.
5. ✅ **Move to FederalRunner** - Phase 2: Execution agent

---

## Additional Resources

- **[FederalScout README](../../mcp-servers/federalscout-mcp/README.md)** - Tool documentation
- **[Agent Instructions](../../agents/federalscout-instructions.md)** - Discovery workflow patterns
- **[Discovery Requirements](../../requirements/discovery/DISCOVERY_REQUIREMENTS.md)** - Detailed specifications
- **[Demo Mode Script](../../mcp-servers/federalscout-mcp/scripts/README.md)** - Browser setup guide

---

**Built with ❤️ for accessible government services**

*Part of the FormFlow project - Making government forms conversationally accessible*
