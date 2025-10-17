# FederalRunner Execution Agent

Execute government form wizards atomically with natural language input.

## Overview

FederalRunner is the execution component of the Multi-Agent Federal Form Automation system. It takes discovered wizard structures (from FederalScout) and executes them atomically with user-provided data, returning official government results.

**Key Features:**
- ✅ Atomic execution (launch → fill all pages → extract results → close)
- ✅ Universal design (works with ANY wizard conforming to schema)
- ✅ Two-phase browser support (Chromium non-headless, WebKit headless)
- ✅ Cloud Run ready (stateless, serverless)
- ✅ OAuth 2.1 authentication
- ✅ Audit trail screenshots

## Configuration

### Environment Variable Loading

FederalRunner uses `pydantic-settings` for flexible configuration loading with the following **priority order** (highest to lowest):

1. **Constructor arguments** - `FederalRunnerConfig(headless=True)`
2. **Environment variables** - `FEDERALRUNNER_HEADLESS=true`
3. **.env file** - `FEDERALRUNNER_HEADLESS=false`
4. **Default values** - `headless=False`

This works seamlessly across all deployment scenarios:

#### Local pytest Tests
```bash
# Loads from .env file + test overrides
pytest tests/test_execution_local.py -v
```

The test uses `get_test_config()` which **overrides** .env settings:
```python
# Phase 1: Non-headless (debugging)
config = get_test_config(headless=False, browser_type="chromium")

# Phase 2: Headless (production validation)
config = get_test_config(headless=True, browser_type="webkit")
```

#### Local MCP with Claude Desktop
```bash
# Loads .env from working directory
uvicorn src.server:app --reload
```

Claude Desktop MCP configuration:
```json
{
  "mcpServers": {
    "federalrunner": {
      "url": "http://localhost:8080/mcp"
    }
  }
}
```

Settings in `.env` are automatically loaded when server starts.

#### Cloud Run Deployment
```bash
# Uses environment variables from Cloud Run configuration
gcloud run deploy federalrunner-mcp \
  --set-env-vars FEDERALRUNNER_HEADLESS=true,FEDERALRUNNER_BROWSER_TYPE=webkit
```

No .env file needed - environment variables set in Cloud Run take precedence.

### Configuration Options

All configuration options can be set via environment variables with the `FEDERALRUNNER_` prefix:

```bash
# Browser Settings
FEDERALRUNNER_BROWSER_TYPE=chromium     # chromium, firefox, or webkit
FEDERALRUNNER_HEADLESS=false            # false (local), true (production)
FEDERALRUNNER_SLOW_MO=0                 # Slow down actions (ms)

# Execution Settings
FEDERALRUNNER_EXECUTION_TIMEOUT=60      # Max execution time (seconds)

# Screenshot Settings
FEDERALRUNNER_SCREENSHOT_QUALITY=80     # JPEG quality (1-100)
FEDERALRUNNER_SCREENSHOT_MAX_SIZE_KB=100
FEDERALRUNNER_SAVE_SCREENSHOTS=true     # Save to disk for debugging

# Viewport Size
FEDERALRUNNER_VIEWPORT_WIDTH=1280
FEDERALRUNNER_VIEWPORT_HEIGHT=1024

# Paths (optional - auto-detected)
FEDERALRUNNER_WORKSPACE_ROOT=/path/to/workspace
FEDERALRUNNER_WIZARDS_DIR=/path/to/wizards
FEDERALRUNNER_LOG_DIR=/path/to/logs
FEDERALRUNNER_SCREENSHOT_DIR=/path/to/screenshots

# Logging
LOG_LEVEL=INFO                      # DEBUG, INFO, WARNING, ERROR
```

### Browser Strategy

**CRITICAL:** FSA website blocks headless Chromium and Firefox.

| Environment | Browser | Headless | Purpose |
|-------------|---------|----------|---------|
| **Local pytest (Phase 1)** | Chromium | ❌ False | Debugging with visible browser |
| **Local pytest (Phase 2)** | WebKit | ✅ True | Production validation |
| **Local MCP Server** | Chromium | ❌ False | Visual validation with Claude Desktop |
| **Cloud Run Production** | WebKit | ✅ True | Production (FSA compatible) |

## Quick Start

### 1. Install Dependencies

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install webkit chromium
```

### 2. Configure Environment

```bash
# Copy example configuration
cp .env.example .env

# Edit .env for your local setup
# Default settings work for local development
```

### 3. Verify Configuration Loading

```bash
# Run configuration test
python tests/test_config_loading.py
```

Expected output:
```
============================================================
FederalRunner Configuration Loading Tests
============================================================

✓ Config loaded from .env file
✓ Environment variables override .env file
✓ Constructor arguments have highest priority
✓ Phase 1 config: Non-headless Chromium
✓ Phase 2 config: Headless WebKit
✓ Production config: Headless WebKit for Cloud Run

============================================================
All configuration tests passed! ✓
============================================================
```

## Project Structure

```
federalrunner-mcp/
├── src/
│   ├── __init__.py
│   ├── models.py              # Shared wizard structure models
│   ├── config.py              # Configuration management
│   ├── logging_config.py      # Cloud Run compatible logging
│   ├── playwright_client.py   # Atomic execution client ✅
│   ├── schema_validator.py    # Schema validation (replaces field_mapper) ✅
│   ├── execution_tools.py     # MCP tools ✅
│   ├── server.py              # FastAPI MCP server (TODO)
│   └── auth.py                # OAuth 2.1 (TODO)
├── tests/
│   ├── test_config_loading.py          # Config verification ✅
│   ├── test_execution_local.py         # Execution tests ✅
│   └── run_tests.sh                    # Test runner script ✅
├── .env                       # Local configuration (git-ignored)
├── .env.example               # Configuration template
├── .gitignore                 # Git ignore rules
├── requirements.txt           # Python dependencies
├── pytest.ini                 # Pytest configuration
└── README.md                  # This file
```

## Development Status

- ✅ **Step 1: Core Infrastructure** - COMPLETE
  - ✅ Project structure
  - ✅ Configuration management
  - ✅ Logging setup
  - ✅ Shared models (WizardStructure)

- ✅ **Step 2: Playwright Execution Client** - COMPLETE
  - ✅ Atomic execution pattern (launch → fill → extract → close)
  - ✅ Browser launch (Chromium/WebKit)
  - ✅ Field interaction logic (all interaction types)
  - ✅ Screenshot capture and optimization
  - ✅ Result extraction framework

- ✅ **Step 3: Schema Validator** - COMPLETE
  - ✅ Replaces field_mapper.py (no hardcoded mappings!)
  - ✅ JSON Schema validation
  - ✅ Claude-friendly error messages
  - ✅ Schema enhancement for Claude

- ✅ **Step 4: Execution Tools (MCP)** - COMPLETE
  - ✅ federalrunner_list_wizards()
  - ✅ federalrunner_get_wizard_info() (returns schema)
  - ✅ federalrunner_execute_wizard() (validates + executes)
  - ✅ Contract-first pattern implementation

- ✅ **Step 5: Local Testing** - COMPLETE
  - ✅ 14 comprehensive tests
  - ✅ Unit tests (schema, validation, mapping)
  - ✅ Integration tests (Playwright execution)
  - ✅ End-to-end tests (complete MCP workflow)
  - ✅ Error handling tests

- ⬜ **Step 6: FastAPI MCP Server** - PENDING
- ⬜ **Step 7: Claude Desktop Integration** - PENDING
- ⬜ **Step 8: Cloud Run Deployment** - PENDING

## Testing

FederalRunner includes comprehensive tests covering unit tests, integration tests, and end-to-end execution tests.

### Quick Start

```bash
# Run all tests with automated test runner
./run_tests.sh

# Or run manually
pytest tests/test_execution_local.py -v
```

### Test Coverage

- ✅ **14 Tests Total**
  - 6 Unit tests (schema loading, validation, mapping)
  - 2 MCP tool tests (list_wizards, get_wizard_info)
  - 2 Integration tests (Playwright execution: Phase 1 & 2)
  - 2 End-to-end tests (complete contract-first workflow)
  - 2 Error handling tests

### Two-Phase Testing Approach

**Phase 1: Non-Headless Chromium (Visual Debugging)**
```bash
# Watch the browser execute the FSA wizard!
pytest tests/test_execution_local.py::test_playwright_client_atomic_execution_non_headless -v -s
```

**Phase 2: Headless WebKit (Production Validation)**
```bash
# Headless execution with FSA-compatible browser
pytest tests/test_execution_local.py::test_playwright_client_atomic_execution_headless -v -s
```

### Detailed Test Documentation

For comprehensive testing instructions, troubleshooting, and test details, see:
**[docs/execution/TEST_INSTRUCTIONS.md](../../docs/execution/TEST_INSTRUCTIONS.md)**

## License

MIT
