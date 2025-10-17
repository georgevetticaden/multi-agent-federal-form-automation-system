# FederalRunner Execution Agent

Execute government form wizards atomically with natural language input.

## Overview

FederalRunner is the execution component of the Multi-Agent Federal Form Automation system. It takes discovered wizard structures (from FederalScout) and executes them atomically with user-provided data, returning official government results.

**Key Features:**
- ✅ Atomic execution (launch → fill all pages → extract results → close)
- ✅ Universal design (works with ANY wizard conforming to schema)
- ✅ Two-phase browser support (Chromium non-headless, WebKit headless)
- ✅ Contract-first pattern (schema validation before execution)
- ✅ Cloud Run ready (stateless, serverless)
- ✅ Audit trail screenshots

## Quick Start

### 1. Run Setup Script

The setup script will configure your complete development environment:

```bash
cd mcp-servers/federalrunner-mcp
./scripts/setup.sh
```

**What the setup script does:**
- ✅ Finds Python 3.10+ (tries 3.13, 3.12, 3.11, 3.10)
- ✅ Creates virtual environment
- ✅ Installs all dependencies (production + test)
- ✅ Installs Playwright browsers (WebKit + Chromium)
- ✅ Creates `.env` file from `.env.example`
- ✅ Ready to run tests!

### 2. Run Tests

```bash
# Activate virtual environment (if not already active)
source venv/bin/activate

# Run all tests with automated test runner
./run_tests.sh

# Or run specific tests
pytest tests/test_execution_local.py -v
```

### 3. Detailed Testing Instructions

For comprehensive testing instructions, see:
**[docs/execution/TEST_INSTRUCTIONS.md](../../docs/execution/TEST_INSTRUCTIONS.md)**

---

## Configuration

FederalRunner uses `pydantic-settings` for flexible configuration loading with the following **priority order** (highest to lowest):

1. **Constructor arguments** - `FederalRunnerConfig(headless=True)`
2. **Environment variables** - `FEDERALRUNNER_HEADLESS=true`
3. **.env file** - `FEDERALRUNNER_HEADLESS=false`
4. **Default values** - `headless=False`

### Configuration Options

Edit `.env` file or set environment variables with `FEDERALRUNNER_` prefix:

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

# Logging
LOG_LEVEL=INFO                          # DEBUG, INFO, WARNING, ERROR
```

### Browser Strategy

**CRITICAL:** FSA website blocks headless Chromium and Firefox.

| Environment | Browser | Headless | Purpose |
|-------------|---------|----------|---------|
| **Local pytest (Phase 1)** | Chromium | ❌ False | Debugging with visible browser |
| **Local pytest (Phase 2)** | WebKit | ✅ True | Production validation |
| **Local MCP Server** | Chromium | ❌ False | Visual validation with Claude Desktop |
| **Cloud Run Production** | WebKit | ✅ True | Production (FSA compatible) |

---

## Project Structure

```
federalrunner-mcp/
├── scripts/
│   └── setup.sh                 # Development environment setup ✅
├── src/
│   ├── models.py                # Shared wizard structure models ✅
│   ├── config.py                # Configuration management ✅
│   ├── logging_config.py        # Cloud Run compatible logging ✅
│   ├── playwright_client.py     # Atomic execution client ✅
│   ├── schema_validator.py      # Schema validation (replaces field_mapper) ✅
│   ├── execution_tools.py       # MCP tools ✅
│   ├── server.py                # FastAPI MCP server (TODO)
│   └── auth.py                  # OAuth 2.1 (TODO)
├── tests/
│   ├── test_execution_local.py  # Execution tests ✅
│   └── run_tests.sh             # Test runner script ✅
├── .env.example                 # Configuration template
├── requirements.txt             # Production dependencies
├── requirements-test.txt        # Test dependencies
├── pytest.ini                   # Pytest configuration
└── README.md                    # This file
```

---

## Development Status

- ✅ **Step 1: Core Infrastructure** - COMPLETE
- ✅ **Step 2: Playwright Execution Client** - COMPLETE
- ✅ **Step 3: Schema Validator** - COMPLETE
- ✅ **Step 4: Execution Tools (MCP)** - COMPLETE
- ✅ **Step 5: Local Testing** - COMPLETE (14 tests)
- ⬜ **Step 6: FastAPI MCP Server** - PENDING
- ⬜ **Step 7: Claude Desktop Integration** - PENDING
- ⬜ **Step 8: Cloud Run Deployment** - PENDING

---

## Testing

### Quick Test Commands

```bash
# Run all tests (automated test runner)
./run_tests.sh

# Run all tests manually
pytest tests/test_execution_local.py -v

# Run fast unit tests only (no browser)
pytest tests/test_execution_local.py -k "not slow and not e2e" -v

# Run Phase 1 only (visible browser - debugging)
pytest tests/test_execution_local.py::test_playwright_client_atomic_execution_non_headless -v -s

# Run Phase 2 only (headless - production validation)
pytest tests/test_execution_local.py::test_playwright_client_atomic_execution_headless -v -s
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
- Watch the browser execute the FSA wizard in real-time
- Perfect for debugging and verifying field interactions

**Phase 2: Headless WebKit (Production Validation)**
- Tests production configuration
- WebKit headless mode works with FSA (Chromium doesn't)

**Detailed instructions:** [docs/execution/TEST_INSTRUCTIONS.md](../../docs/execution/TEST_INSTRUCTIONS.md)

---

## License

MIT
