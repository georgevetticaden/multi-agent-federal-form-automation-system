# Docker WebKit Compatibility Fix

## Problem

FederalRunner deployment to Google Cloud Run failed with browser launch error:

```
BrowserType.launch:
╔══════════════════════════════════════════════════════╗
║ Host system is missing dependencies to run browsers. ║
║ Missing libraries:                                   ║
║     libicudata.so.66                                 ║
║     libicui18n.so.66                                 ║
║     libicuuc.so.66                                   ║
║     libjpeg.so.8                                     ║
║     libwebp.so.6                                     ║
║     libffi.so.7                                      ║
║     libx264.so                                       ║
╚══════════════════════════════════════════════════════╝
```

## Root Cause

The Dockerfile was using `python:3.11-slim` which is based on **Debian Trixie** (testing/unstable). This distribution has incompatible library versions:

- **Debian Trixie**: Has `libicu76`, `libffi8`, etc. (newer versions with time64 transition)
- **Playwright WebKit**: Built for Ubuntu 20.04, expects `libicu66`, `libjpeg.so.8`, etc.

The build log showed:
```
BEWARE: your OS is not officially supported by Playwright;
downloading fallback build for ubuntu20.04-x64.
```

## Solution

Updated `/mcp-servers/federalrunner-mcp/Dockerfile` with three changes:

### 1. Base Image - Switch to Bookworm (Stable)

**Before:**
```dockerfile
FROM python:3.11-slim as base
```

**After:**
```dockerfile
FROM python:3.11-slim-bookworm as base
```

**Reason**: Bookworm (Debian 12 stable) has library versions closer to Ubuntu 20.04 than Trixie.

### 2. Playwright Installation - Add --with-deps

**Before:**
```dockerfile
RUN playwright install webkit
```

**After:**
```dockerfile
RUN playwright install --with-deps webkit
```

**Reason**: The `--with-deps` flag automatically detects and installs the exact system libraries Playwright WebKit needs, avoiding manual version matching.

### 3. Library Names - Remove Trixie-specific Suffixes

**Before:**
```dockerfile
libasound2t64
libatk-bridge2.0-0t64
libatk1.0-0t64
...
libicu76
libevent-2.1-7t64
```

**After:**
```dockerfile
libasound2
libatk-bridge2.0-0
libatk1.0-0
...
libicu72
libevent-2.1-7
```

**Reason**: The `t64` suffix was specific to Debian Trixie's time64 transition. Bookworm uses standard names.

## Testing

After this fix, redeploy to Google Cloud Run:

```bash
cd /Users/aju/Dropbox/Development/Git/10-17-25-multi-agent-federal-form-automation-system/multi-agent-federal-form-automation-system/mcp-servers/federalrunner-mcp

./scripts/deploy-to-cloud-run.sh
```

Expected outcome:
- ✅ Build completes without Playwright warnings
- ✅ WebKit launches successfully in Cloud Run
- ✅ Browser automation works in headless mode
- ✅ FSA wizard execution succeeds

## Verification Commands

After deployment, monitor logs for successful Playwright initialization:

```bash
# View real-time logs
gcloud run services logs tail federalrunner-mcp --region us-central1

# Check for Playwright initialization
gcloud run services logs tail federalrunner-mcp --region us-central1 | grep -i 'playwright'

# Verify no library errors
gcloud run services logs tail federalrunner-mcp --region us-central1 | grep -i 'missing libraries'
```

## Related Files

- `/mcp-servers/federalrunner-mcp/Dockerfile` - Updated Docker configuration
- `/mcp-servers/federalrunner-mcp/scripts/deploy-to-cloud-run.sh` - Deployment script
- `/docs/blog-demo/federalrunner_demo_realistic.md` - Production demo script

## Technical Background

**Debian Distribution Timeline:**
- **Trixie** (testing/unstable) - Newest packages, time64 transition
- **Bookworm** (stable, Debian 12) - Current stable release
- **Bullseye** (oldstable, Debian 11) - Previous stable release

**Playwright Browser Support:**
- WebKit builds target Ubuntu 20.04 LTS (released April 2020)
- Requires specific library versions from that era
- `--with-deps` flag handles compatibility automatically

**Why WebKit?**
The FSA website blocks headless Chromium/Firefox. WebKit is the only browser that works in headless mode for FSA wizards.

## Next Steps

1. ✅ Fix applied to Dockerfile
2. ⏳ Deploy to Google Cloud Run
3. ⏳ Test from Claude.ai web interface
4. ⏳ Verify mobile sync (Android)
5. ⏳ Record Galaxy Fold 7 voice demo
