# FSA Session Restoration Testing with Playwright (Python)

## Project Goal

Test whether the Federal Student Aid (FSA) Estimator's wizard sessions can be restored using cookies alone, which is critical for building a universal government calculator agent that works reliably on Google Cloud Run.

## The Problem We're Solving

Government form wizards like FSA maintain session state across multiple pages:
- **Starting URL**: `https://studentaid.gov/aid-estimator/`
- **Page 1**: `https://studentaid.gov/aid-estimator/estimate/student-information`
- **Page 2**: `https://studentaid.gov/aid-estimator/estimate/student-information/personal-circumstances`
- **Page 3+**: Additional wizard pages...

Direct navigation to Page 2 URL redirects back to the start - the server validates session state. We need to determine if we can restore these sessions by saving and restoring cookies.

## Project Structure

```
10-14-25-fsa-session-restoration-test/
├── CLAUDE.md                           # This file - testing instructions
├── requirements.txt                    # Python dependencies
├── test_basic_navigation.py           # Test 1: Understand normal flow
├── test_direct_url_access.py          # Test 2: Verify redirect behavior
├── test_cookie_restoration.py         # Test 3: Core session restoration test
├── test_multi_page_restoration.py     # Test 4: Multiple page restoration
├── test_storage_inspection.py         # Test 5: Check localStorage/sessionStorage
├── screenshots/                        # Visual evidence directory
└── session_data/                      # Saved cookies and storage data
```

## Setup Instructions

### 1. Create Virtual Environment

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate  # On macOS/Linux
# OR
venv\Scripts\activate     # On Windows
```

### 2. Install Dependencies

Create `requirements.txt`:
```
playwright==1.47.0
```

Install:
```bash
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium
```

### 3. Create Test Files

Create five Python test files (provided below) that systematically test FSA session behavior.

## Test Suite Overview

### Test 1: Basic Navigation Flow
**Purpose**: Understand how FSA wizard normally works
**File**: `test_basic_navigation.py`
**What it does**: 
- Navigate to FSA starting page
- Click "Start Estimate" button
- Fill Page 1 with minimal data
- Click "Continue" to Page 2
- Take screenshots at each step
- Inspect cookies after each navigation

### Test 2: Direct URL Access
**Purpose**: Confirm direct page access is blocked
**File**: `test_direct_url_access.py`
**What it does**:
- Try to navigate directly to Page 2 URL
- Verify it redirects back to start
- Proves we need session state

### Test 3: Cookie-Based Session Restoration ⭐ (Critical Test)
**Purpose**: Test if cookies alone can restore session
**File**: `test_cookie_restoration.py`
**What it does**:
1. Browser 1: Navigate to FSA, fill Page 1, click Continue to Page 2
2. Save all cookies from Browser 1
3. Close Browser 1 completely
4. Wait 5 seconds
5. Browser 2: Create new browser, restore cookies
6. Try to navigate to Page 2 URL
7. Check if we're on Page 2 or redirected to start

**Success criteria**: Browser 2 successfully loads Page 2 without redirect

### Test 4: Multi-Page Restoration
**Purpose**: Test restoration across multiple wizard pages
**File**: `test_multi_page_restoration.py`
**What it does**:
- Progress through Pages 1, 2, 3
- Restore session between each page
- Verify session persists across multiple restorations

### Test 5: Storage Inspection
**Purpose**: Check if FSA uses localStorage/sessionStorage
**File**: `test_storage_inspection.py`
**What it does**:
- Navigate through wizard
- Inspect localStorage contents at each page
- Inspect sessionStorage contents at each page
- Determine if we need to preserve more than just cookies

---

## Test File: test_basic_navigation.py

```python
import asyncio
import json
import os
from pathlib import Path
from playwright.async_api import async_playwright

async def test_basic_navigation():
    print('=== TEST 1: Basic Navigation Flow ===\n')
    
    # Create directories
    screenshot_dir = Path(__file__).parent / 'screenshots' / 'test1'
    screenshot_dir.mkdir(parents=True, exist_ok=True)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, slow_mo=1000)
        page = await browser.new_page()
        
        try:
            # Step 1: Navigate to FSA starting page
            print('Step 1: Navigating to FSA Estimator...')
            await page.goto('https://studentaid.gov/aid-estimator/')
            await page.wait_for_load_state('networkidle')
            await page.screenshot(path=screenshot_dir / '01_landing_page.png')
            print(f'  ✓ Landed on: {page.url}')
            
            # Check initial cookies
            cookies_start = await page.context.cookies()
            print(f'  ✓ Initial cookies: {len(cookies_start)}')
            save_cookies(cookies_start, screenshot_dir, 'cookies_start.json')
            
            # Step 2: Click "Start Estimate" button
            print('\nStep 2: Clicking "Start Estimate"...')
            start_button = page.locator('text=Start Estimate').first
            await start_button.click()
            await page.wait_for_load_state('networkidle')
            await page.screenshot(path=screenshot_dir / '02_page1_loaded.png')
            print(f'  ✓ Navigated to: {page.url}')
            
            # Check cookies after navigation
            cookies_page1 = await page.context.cookies()
            print(f'  ✓ Page 1 cookies: {len(cookies_page1)}')
            save_cookies(cookies_page1, screenshot_dir, 'cookies_page1.json')
            
            # Step 3: Fill minimal data on Page 1
            print('\nStep 3: Filling Page 1 student information...')
            
            # Fill birth date
            await page.select_option('select[name*="month" i]', '05')
            await page.select_option('select[name*="day" i]', '15')
            await page.fill('input[name*="year" i]', '2007')
            
            # Select state
            await page.select_option('select[name*="state" i]', 'IL')
            
            # Select grade level (wait for it to appear)
            await page.wait_for_selector('select[name*="grade" i]', timeout=5000)
            await page.select_option('select[name*="grade" i]', index=1)
            
            await page.screenshot(path=screenshot_dir / '03_page1_filled.png')
            print('  ✓ Page 1 form filled')
            
            # Step 4: Click Continue to Page 2
            print('\nStep 4: Clicking Continue to Page 2...')
            continue_button = page.locator('button:has-text("Continue")').first
            await continue_button.click()
            await page.wait_for_load_state('networkidle')
            await page.screenshot(path=screenshot_dir / '04_page2_loaded.png')
            print(f'  ✓ Navigated to: {page.url}')
            
            # Check cookies on Page 2
            cookies_page2 = await page.context.cookies()
            print(f'  ✓ Page 2 cookies: {len(cookies_page2)}')
            save_cookies(cookies_page2, screenshot_dir, 'cookies_page2.json')
            
            # Compare cookies
            print('\n=== Cookie Analysis ===')
            print(f'Start → Page 1: Added {len(cookies_page1) - len(cookies_start)} cookies')
            print(f'Page 1 → Page 2: Added {len(cookies_page2) - len(cookies_page1)} cookies')
            
            # Show session cookies
            session_cookies = [c for c in cookies_page2 
                             if 'session' in c['name'].lower() 
                             or 'jsessionid' in c['name'].lower()]
            cookie_names = ', '.join([c['name'] for c in session_cookies]) or 'None found'
            print(f'Session-related cookies: {cookie_names}')
            
            print('\n✅ TEST 1 PASSED: Successfully navigated through normal flow')
            
        except Exception as error:
            print(f'\n❌ TEST 1 FAILED: {error}')
            await page.screenshot(path=screenshot_dir / 'error.png')
        finally:
            await browser.close()

def save_cookies(cookies, directory, filename):
    filepath = directory / filename
    with open(filepath, 'w') as f:
        json.dump(cookies, f, indent=2)

if __name__ == '__main__':
    asyncio.run(test_basic_navigation())
```

---

## Test File: test_direct_url_access.py

```python
import asyncio
from pathlib import Path
from playwright.async_api import async_playwright

async def test_direct_url_access():
    print('=== TEST 2: Direct URL Access (Should Redirect) ===\n')
    
    screenshot_dir = Path(__file__).parent / 'screenshots' / 'test2'
    screenshot_dir.mkdir(parents=True, exist_ok=True)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, slow_mo=1000)
        page = await browser.new_page()
        
        try:
            # Try to access Page 2 directly
            page2_url = 'https://studentaid.gov/aid-estimator/estimate/student-information/personal-circumstances'
            
            print('Attempting to access Page 2 directly...')
            print(f'Target URL: {page2_url}')
            
            await page.goto(page2_url)
            await page.wait_for_load_state('networkidle')
            await page.screenshot(path=screenshot_dir / 'direct_access_result.png')
            
            final_url = page.url
            print(f'Final URL: {final_url}')
            
            if final_url == page2_url:
                print('\n⚠️  UNEXPECTED: Direct access worked! No session validation.')
            else:
                print(f'\n✅ EXPECTED: Redirected to: {final_url}')
                print('   This confirms FSA requires session state')
            
        except Exception as error:
            print(f'\n❌ TEST 2 FAILED: {error}')
            await page.screenshot(path=screenshot_dir / 'error.png')
        finally:
            await browser.close()

if __name__ == '__main__':
    asyncio.run(test_direct_url_access())
```

---

## Test File: test_cookie_restoration.py ⭐

```python
import asyncio
import json
import time
from pathlib import Path
from playwright.async_api import async_playwright

async def test_cookie_restoration():
    print('=== TEST 3: Cookie-Based Session Restoration ===\n')
    
    screenshot_dir = Path(__file__).parent / 'screenshots' / 'test3'
    session_dir = Path(__file__).parent / 'session_data'
    screenshot_dir.mkdir(parents=True, exist_ok=True)
    session_dir.mkdir(parents=True, exist_ok=True)
    
    async with async_playwright() as p:
        # PHASE 1: Navigate to Page 2 in Browser 1
        print('PHASE 1: Browser 1 - Navigate to Page 2')
        print('─' * 50)
        
        browser1 = await p.chromium.launch(headless=False, slow_mo=1000)
        page1 = await browser1.new_page()
        
        try:
            # Navigate to FSA
            print('1. Navigating to FSA...')
            await page1.goto('https://studentaid.gov/aid-estimator/')
            await page1.wait_for_load_state('networkidle')
            
            # Click Start Estimate
            print('2. Clicking Start Estimate...')
            await page1.locator('text=Start Estimate').first.click()
            await page1.wait_for_load_state('networkidle')
            await page1.screenshot(path=screenshot_dir / 'browser1_page1.png')
            page1_url = page1.url
            print(f'   Page 1 URL: {page1_url}')
            
            # Fill Page 1 with minimal data
            print('3. Filling Page 1...')
            await page1.select_option('select[name*="month" i]', '05')
            await page1.select_option('select[name*="day" i]', '15')
            await page1.fill('input[name*="year" i]', '2007')
            await page1.select_option('select[name*="state" i]', 'IL')
            await page1.wait_for_selector('select[name*="grade" i]', timeout=5000)
            await page1.select_option('select[name*="grade" i]', index=1)
            
            # Click Continue to Page 2
            print('4. Clicking Continue to Page 2...')
            await page1.locator('button:has-text("Continue")').first.click()
            await page1.wait_for_load_state('networkidle')
            await page1.screenshot(path=screenshot_dir / 'browser1_page2.png')
            page2_url = page1.url
            print(f'   Page 2 URL: {page2_url}')
            
            # Save cookies from Browser 1
            print('5. Saving cookies from Browser 1...')
            saved_cookies = await page1.context.cookies()
            cookies_path = session_dir / 'saved_cookies.json'
            with open(cookies_path, 'w') as f:
                json.dump(saved_cookies, f, indent=2)
            print(f'   Saved {len(saved_cookies)} cookies to: {cookies_path}')
            
            # Display important cookies
            session_cookies = [c for c in saved_cookies 
                             if 'session' in c['name'].lower() 
                             or 'jsessionid' in c['name'].lower()
                             or 'token' in c['name'].lower()]
            cookie_names = ', '.join([c['name'] for c in session_cookies]) or 'None found'
            print(f'   Session cookies: {cookie_names}')
            
            # Close Browser 1
            print('6. Closing Browser 1...')
            await browser1.close()
            print('   ✓ Browser 1 closed completely\n')
            
            # Wait to simulate session gap
            print('Waiting 5 seconds to simulate session gap...\n')
            await asyncio.sleep(5)
            
            # PHASE 2: Restore session in Browser 2
            print('PHASE 2: Browser 2 - Restore Session')
            print('─' * 50)
            
            browser2 = await p.chromium.launch(headless=False, slow_mo=1000)
            context2 = await browser2.new_context()
            page2 = await context2.new_page()
            
            # Restore cookies
            print('1. Restoring cookies to Browser 2...')
            await context2.add_cookies(saved_cookies)
            print(f'   ✓ Restored {len(saved_cookies)} cookies')
            
            # Try to navigate to Page 2 URL
            print('2. Attempting to navigate to Page 2 URL...')
            print(f'   Target: {page2_url}')
            await page2.goto(page2_url)
            await page2.wait_for_load_state('networkidle')
            await page2.screenshot(path=screenshot_dir / 'browser2_restoration_result.png')
            
            final_url = page2.url
            print(f'   Final URL: {final_url}')
            
            # RESULT ANALYSIS
            print('\n' + '=' * 50)
            print('RESULT ANALYSIS')
            print('=' * 50)
            
            if final_url == page2_url or 'personal-circumstances' in final_url:
                print('✅ SUCCESS: Session restored via cookies!')
                print('   Browser 2 successfully loaded Page 2')
                print('   This means we can use MongoDB for cookie storage')
                return True
            else:
                print('❌ FAILED: Session NOT restored')
                print(f'   Redirected to: {final_url}')
                print('   FSA requires more than just cookies for session')
                print('   Need alternative approach (external browser service)')
                return False
            
        except Exception as error:
            print(f'\n❌ TEST 3 ERROR: {error}')
            await page2.screenshot(path=screenshot_dir / 'error.png')
            return False
        finally:
            await browser2.close()

if __name__ == '__main__':
    success = asyncio.run(test_cookie_restoration())
    exit(0 if success else 1)
```

---

## Test File: test_multi_page_restoration.py

```python
import asyncio
import json
from pathlib import Path
from datetime import datetime
from playwright.async_api import async_playwright

async def save_session(page, step, session_dir):
    """Save current page session (cookies + URL)"""
    cookies = await page.context.cookies()
    session_data = {
        'url': page.url,
        'cookies': cookies,
        'timestamp': datetime.now().isoformat()
    }
    session_file = session_dir / f'session_step{step}.json'
    with open(session_file, 'w') as f:
        json.dump(session_data, f, indent=2)
    return session_file

async def restore_session(playwright, session_file):
    """Restore session from saved file"""
    with open(session_file, 'r') as f:
        session = json.load(f)
    
    browser = await playwright.chromium.launch(headless=False, slow_mo=1000)
    context = await browser.new_context()
    page = await context.new_page()
    await context.add_cookies(session['cookies'])
    await page.goto(session['url'])
    await page.wait_for_load_state('networkidle')
    return browser, page

async def test_multi_page_restoration():
    print('=== TEST 4: Multi-Page Session Restoration ===\n')
    
    screenshot_dir = Path(__file__).parent / 'screenshots' / 'test4'
    session_dir = Path(__file__).parent / 'session_data'
    screenshot_dir.mkdir(parents=True, exist_ok=True)
    session_dir.mkdir(parents=True, exist_ok=True)
    
    async with async_playwright() as p:
        browser = None
        page = None
        
        try:
            # Step 1: Navigate to Page 1
            print('Step 1: Navigate to Page 1')
            browser = await p.chromium.launch(headless=False, slow_mo=1000)
            page = await browser.new_page()
            
            await page.goto('https://studentaid.gov/aid-estimator/')
            await page.locator('text=Start Estimate').first.click()
            await page.wait_for_load_state('networkidle')
            await page.screenshot(path=screenshot_dir / 'step1_page1.png')
            print(f'  ✓ On Page 1: {page.url}')
            
            # Fill and continue to Page 2
            print('\nStep 2: Fill Page 1 and continue to Page 2')
            await page.select_option('select[name*="month" i]', '05')
            await page.select_option('select[name*="day" i]', '15')
            await page.fill('input[name*="year" i]', '2007')
            await page.select_option('select[name*="state" i]', 'IL')
            await page.wait_for_selector('select[name*="grade" i]', timeout=5000)
            await page.select_option('select[name*="grade" i]', index=1)
            await page.locator('button:has-text("Continue")').first.click()
            await page.wait_for_load_state('networkidle')
            await page.screenshot(path=screenshot_dir / 'step2_page2.png')
            print(f'  ✓ On Page 2: {page.url}')
            
            # Save session after Page 2
            session_file = await save_session(page, 2, session_dir)
            print(f'  ✓ Saved session to: {session_file}')
            
            # Close browser
            await browser.close()
            print('  ✓ Browser closed')
            
            # Wait and restore
            print('\nStep 3: Wait and restore session')
            await asyncio.sleep(3)
            
            browser, page = await restore_session(p, session_file)
            await page.screenshot(path=screenshot_dir / 'step3_restored.png')
            
            if 'personal-circumstances' in page.url:
                print(f'  ✅ Session restored! On: {page.url}')
                
                # Try to continue to Page 3
                print('\nStep 4: Fill Page 2 and continue to Page 3')
                # Select marital status
                await page.locator('input[value="Yes"]').first.click()  # Married
                await page.locator('button:has-text("Continue")').first.click()
                await page.wait_for_load_state('networkidle')
                await page.screenshot(path=screenshot_dir / 'step4_page3.png')
                print(f'  ✓ On Page 3: {page.url}')
                
                # Save session after Page 3
                session_file = await save_session(page, 3, session_dir)
                print(f'  ✓ Saved session to: {session_file}')
                
                # Close and restore again
                await browser.close()
                print('  ✓ Browser closed')
                
                print('\nStep 5: Second restoration test')
                await asyncio.sleep(3)
                
                browser, page = await restore_session(p, session_file)
                await page.screenshot(path=screenshot_dir / 'step5_restored_again.png')
                
                if 'parent-marital-status' in page.url:
                    print(f'  ✅ Second restoration successful! On: {page.url}')
                    print('\n✅ TEST 4 PASSED: Multi-page restoration works!')
                else:
                    print(f'  ❌ Second restoration failed. On: {page.url}')
                    print('\n❌ TEST 4 FAILED: Cannot restore after multiple pages')
            else:
                print(f'  ❌ First restoration failed. On: {page.url}')
                print('\n❌ TEST 4 FAILED: Cannot restore session')
            
        except Exception as error:
            print(f'\n❌ TEST 4 ERROR: {error}')
            if page:
                await page.screenshot(path=screenshot_dir / 'error.png')
        finally:
            if browser:
                await browser.close()

if __name__ == '__main__':
    asyncio.run(test_multi_page_restoration())
```

---

## Test File: test_storage_inspection.py

```python
import asyncio
import json
from pathlib import Path
from playwright.async_api import async_playwright

async def inspect_storage(page, page_name):
    """Inspect localStorage and sessionStorage"""
    print(f'\n--- Storage Inspection: {page_name} ---')
    print(f'URL: {page.url}')
    
    # Get localStorage
    local_storage = await page.evaluate('() => JSON.stringify(localStorage)')
    local_storage_obj = json.loads(local_storage)
    print(f'localStorage keys: {list(local_storage_obj.keys())}')
    if local_storage_obj:
        print('localStorage contents:')
        for key, value in local_storage_obj.items():
            print(f'  {key}: {value[:100]}...' if len(str(value)) > 100 else f'  {key}: {value}')
    
    # Get sessionStorage
    session_storage = await page.evaluate('() => JSON.stringify(sessionStorage)')
    session_storage_obj = json.loads(session_storage)
    print(f'sessionStorage keys: {list(session_storage_obj.keys())}')
    if session_storage_obj:
        print('sessionStorage contents:')
        for key, value in session_storage_obj.items():
            print(f'  {key}: {value[:100]}...' if len(str(value)) > 100 else f'  {key}: {value}')
    
    return {
        'url': page.url,
        'localStorage': local_storage_obj,
        'sessionStorage': session_storage_obj
    }

async def test_storage_inspection():
    print('=== TEST 5: Storage Inspection ===\n')
    
    screenshot_dir = Path(__file__).parent / 'screenshots' / 'test5'
    session_dir = Path(__file__).parent / 'session_data'
    screenshot_dir.mkdir(parents=True, exist_ok=True)
    session_dir.mkdir(parents=True, exist_ok=True)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, slow_mo=1000)
        page = await browser.new_page()
        
        storage_data = []
        
        try:
            # Navigate to FSA
            print('Navigating to FSA Estimator...')
            await page.goto('https://studentaid.gov/aid-estimator/')
            await page.wait_for_load_state('networkidle')
            storage_data.append(await inspect_storage(page, 'Landing Page'))
            
            # Click Start Estimate
            print('\nClicking Start Estimate...')
            await page.locator('text=Start Estimate').first.click()
            await page.wait_for_load_state('networkidle')
            await page.screenshot(path=screenshot_dir / 'page1.png')
            storage_data.append(await inspect_storage(page, 'Page 1'))
            
            # Fill Page 1
            print('\nFilling Page 1...')
            await page.select_option('select[name*="month" i]', '05')
            await page.select_option('select[name*="day" i]', '15')
            await page.fill('input[name*="year" i]', '2007')
            await page.select_option('select[name*="state" i]', 'IL')
            await page.wait_for_selector('select[name*="grade" i]', timeout=5000)
            await page.select_option('select[name*="grade" i]', index=1)
            
            # Click Continue to Page 2
            print('\nContinuing to Page 2...')
            await page.locator('button:has-text("Continue")').first.click()
            await page.wait_for_load_state('networkidle')
            await page.screenshot(path=screenshot_dir / 'page2.png')
            storage_data.append(await inspect_storage(page, 'Page 2'))
            
            # Save all storage data
            storage_file = session_dir / 'storage_inspection.json'
            with open(storage_file, 'w') as f:
                json.dump(storage_data, f, indent=2)
            print(f'\n✓ Saved storage data to: {storage_file}')
            
            # Analysis
            print('\n' + '=' * 50)
            print('STORAGE ANALYSIS')
            print('=' * 50)
            
            has_local_storage = any(s['localStorage'] for s in storage_data)
            has_session_storage = any(s['sessionStorage'] for s in storage_data)
            
            if has_local_storage or has_session_storage:
                print('⚠️  FSA uses browser storage in addition to cookies!')
                if has_local_storage:
                    print('   - localStorage detected')
                if has_session_storage:
                    print('   - sessionStorage detected')
                print('   This means we need to preserve storage along with cookies')
            else:
                print('✅ FSA uses only cookies (no localStorage/sessionStorage)')
                print('   Cookie-only restoration should work')
            
            print('\n✅ TEST 5 COMPLETE: Storage inspection finished')
            
        except Exception as error:
            print(f'\n❌ TEST 5 ERROR: {error}')
            await page.screenshot(path=screenshot_dir / 'error.png')
        finally:
            await browser.close()

if __name__ == '__main__':
    asyncio.run(test_storage_inspection())
```

---

## Running the Tests

### Run Individual Tests

```bash
# Activate virtual environment first
source venv/bin/activate

# Run Test 1: Basic navigation
python test_basic_navigation.py

# Run Test 2: Direct URL access
python test_direct_url_access.py

# Run Test 3: Cookie restoration (CRITICAL)
python test_cookie_restoration.py

# Run Test 4: Multi-page restoration
python test_multi_page_restoration.py

# Run Test 5: Storage inspection
python test_storage_inspection.py
```

### Run All Tests in Sequence

Create `run_all_tests.py`:

```python
import asyncio
import subprocess
import sys

async def run_test(test_file):
    print(f'\n{"=" * 60}')
    print(f'Running: {test_file}')
    print("=" * 60)
    result = subprocess.run([sys.executable, test_file])
    return result.returncode == 0

async def main():
    tests = [
        'test_basic_navigation.py',
        'test_direct_url_access.py',
        'test_cookie_restoration.py',
        'test_multi_page_restoration.py',
        'test_storage_inspection.py'
    ]
    
    results = {}
    for test in tests:
        results[test] = await run_test(test)
    
    print(f'\n{"=" * 60}')
    print('TEST SUMMARY')
    print("=" * 60)
    for test, passed in results.items():
        status = '✅ PASSED' if passed else '❌ FAILED'
        print(f'{test}: {status}')

if __name__ == '__main__':
    asyncio.run(main())
```

Run all tests:
```bash
python run_all_tests.py
```

---

## Analyzing Results

### After Running Tests

1. **Check screenshots/** directory - Visual evidence of each step
2. **Check session_data/** directory - Saved cookies and storage data
3. **Review console output** - Detailed logging of what happened

### Key Questions to Answer

From Test 3 (Cookie Restoration):
- ✅ **If successful**: We can use MongoDB for cookie storage in production
- ❌ **If failed**: Need external browser service or atomic execution

From Test 5 (Storage Inspection):
- If localStorage/sessionStorage used: Need to preserve that too
- If only cookies: Simpler restoration approach

---

## Next Steps Based on Results

### Scenario A: Cookie Restoration Works ✅

```
We can proceed with MongoDB cookie storage:
1. Store cookies in MongoDB after each page
2. Restore cookies for next tool call
3. Also preserve localStorage/sessionStorage if detected
4. Deploy to Cloud Run with confidence
```

### Scenario B: Cookie Restoration Fails ❌

```
Need alternative approach:
1. Use external browser service (Browserless.io)
2. OR use atomic execution (collect all data first, then execute)
3. OR use Cloud Run with session affinity + in-memory storage
```

---

## Debugging Tips

### If tests fail with selector errors:

```python
# Add more wait time
await page.wait_for_timeout(2000)  # Wait 2 seconds

# Try different selectors
await page.locator('button', has_text='Continue').click()
await page.locator('button:has-text("Continue")').click()
await page.get_by_role('button', name='Continue').click()
```

### If pages don't load:

```python
# Increase timeout
await page.goto(url, timeout=60000)  # 60 seconds

# Wait for specific element
await page.wait_for_selector('button:has-text("Continue")', timeout=10000)
```

### View browser console errors:

```python
page.on('console', lambda msg: print(f'CONSOLE: {msg.text}'))
page.on('pageerror', lambda err: print(f'PAGE ERROR: {err}'))
```

---

## Expected Timeline

- Test 1: 2-3 minutes
- Test 2: 1 minute  
- Test 3: 3-4 minutes (most important)
- Test 4: 5-6 minutes
- Test 5: 3-4 minutes

**Total: ~15-20 minutes for full test suite**

---

## Questions to Answer

After running all tests, we'll know:

1. ✅ or ❌ Can FSA sessions be restored via cookies alone?
2. ✅ or ❌ Does FSA use localStorage/sessionStorage?
3. ✅ or ❌ Can we restore across multiple page transitions?
4. ✅ or ❌ Is MongoDB cookie storage viable for production?
5. What's the best architecture for the universal government calculator agent?

---

## Contact

Once tests are complete, share:
- Console output from Test 3 (cookie restoration)
- Screenshots from screenshots/test3/
- Contents of session_data/saved_cookies.json

This will determine the final architecture for the MDCalc Clinical Companion blog!