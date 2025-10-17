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

            # Wait for form to be ready
            await page.wait_for_selector('#fsa_Input_DateOfBirthMonth', timeout=10000)

            # Fill birth date (number inputs, not selects!)
            await page.fill('#fsa_Input_DateOfBirthMonth', '05')
            await page.fill('#fsa_Input_DateOfBirthDay', '15')
            await page.fill('#fsa_Input_DateOfBirthYear', '2007')

            # Select marital status (click the button label div)
            await page.locator('#fsa_Radio_ButtonMaritalStatusUnmarried').click()

            # Fill state (typeahead input)
            await page.fill('#fsa_Typeahead_StateOfResidence', 'Illinois')
            await page.wait_for_timeout(500)
            await page.keyboard.press('Enter')

            # Select college level - wait for the radio to exist (allow hidden), then click via JavaScript
            await page.wait_for_selector('#fsa_Radio_CollegeLevelFreshman', state='attached', timeout=10000)
            await page.wait_for_timeout(500)
            await page.evaluate('document.querySelector("#fsa_Radio_CollegeLevelFreshman").click()')

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
