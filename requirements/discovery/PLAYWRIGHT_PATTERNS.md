# Playwright Automation Patterns for Government Forms

## Purpose

Document proven Playwright patterns discovered through FSA Estimator testing. These patterns solve common challenges with government form automation.

---

## Core Learnings from FSA Testing

### Pattern 1: Hidden Radio Buttons

**Problem:** Radio buttons are often hidden (CSS: `display: none` or `visibility: hidden`)

**FSA Example:**
```html
<input type="radio" 
       id="fsa_Radio_MaritalStatusUnmarried" 
       name="maritalStatus" 
       class="ng-untouched ng-pristine ng-invalid" 
       style="display: none">
```

**Solution:** Use JavaScript `.click()` instead of Playwright's `.click()`

```python
# ❌ This fails - element not visible
await page.click('#fsa_Radio_MaritalStatusUnmarried')

# ✅ This works - JavaScript bypasses visibility check
await page.evaluate('document.getElementById("fsa_Radio_MaritalStatusUnmarried").click()')

# Or more generic:
selector_id = selector.replace('#', '')
await page.evaluate(f'document.getElementById("{selector_id}").click()')
```

**When to use:**
- Radio button inputs with `type="radio"`
- Checkbox inputs with `type="checkbox"`
- Any input with `visibility: hidden` or `display: none`

**Selector pattern in JSON:**
```json
{
  "field_type": "radio",
  "selector": "#fsa_Radio_MaritalStatusUnmarried",
  "interaction": "javascript_click",
  "notes": "Radio input is hidden, must use JavaScript click"
}
```

---

### Pattern 2: Typeahead/Autocomplete Fields

**Problem:** Dropdown-like fields that require typing and selecting from suggestions

**FSA Example:**
```html
<input type="search" 
       id="fsa_Typeahead_StateOfResidence" 
       name="no-name"
       placeholder="Start typing...">
```

**Solution:** Fill + Press Enter

```python
# ❌ This doesn't trigger selection
await page.fill('#fsa_Typeahead_StateOfResidence', 'Illinois')

# ✅ This works - fill then Enter
await page.fill('#fsa_Typeahead_StateOfResidence', 'Illinois')
await page.wait_for_timeout(500)  # Wait for suggestions
await page.keyboard.press('Enter')
```

**When to use:**
- Input fields with `type="search"`
- Fields with "typeahead" or "autocomplete" in ID/class
- Fields that show dropdown suggestions while typing

**Selector pattern in JSON:**
```json
{
  "field_type": "typeahead",
  "selector": "#fsa_Typeahead_StateOfResidence",
  "interaction": "fill_enter",
  "notes": "Type value and press Enter to select from autocomplete"
}
```

---

### Pattern 3: Waiting for Dynamic Elements

**Problem:** Elements appear/load dynamically after page actions

**FSA Example:** Grade level field appears only after state is selected

**Solution:** Wait with `state='attached'` for hidden elements

```python
# ❌ This times out for hidden elements
await page.wait_for_selector('#fsa_Radio_CollegeLevelFreshman', timeout=10000)

# ✅ This works - waits for DOM presence, not visibility
await page.wait_for_selector('#fsa_Radio_CollegeLevelFreshman', 
                             state='attached', 
                             timeout=10000)

# Then use JavaScript click since it's hidden
await page.evaluate('document.getElementById("fsa_Radio_CollegeLevelFreshman").click()')
```

**Wait states:**
- `state='attached'` - Element exists in DOM (can be hidden)
- `state='visible'` - Element is visible (default)
- `state='hidden'` - Wait for element to be hidden

**When to use:**
- Conditional fields that appear based on previous answers
- Elements loaded after AJAX calls
- Hidden elements you'll interact with via JavaScript

---

### Pattern 4: Number Input Fields (Not Dropdowns)

**Problem:** Birthdate fields look like dropdowns but are actually number inputs

**FSA Example:**
```html
<input type="number" 
       id="fsa_Input_DateOfBirthMonth" 
       name="no-name"
       min="1" max="12">
```

**Solution:** Use `.fill()` not `.select_option()`

```python
# ❌ This fails - it's not a select element
await page.select_option('select[name*="month"]', '05')

# ✅ This works - it's an input field
await page.fill('#fsa_Input_DateOfBirthMonth', '05')
await page.fill('#fsa_Input_DateOfBirthDay', '15')
await page.fill('#fsa_Input_DateOfBirthYear', '2007')
```

**Detection:**
- Inspect HTML: `<input type="number">` vs `<select>`
- Test selector: `document.querySelectorAll('select')` returns empty

**Grouped fields pattern:**
```json
{
  "field_type": "group",
  "label": "Date of birth",
  "sub_fields": [
    {
      "field_id": "month",
      "selector": "#fsa_Input_DateOfBirthMonth",
      "field_type": "number",
      "interaction": "fill"
    },
    {
      "field_id": "day",
      "selector": "#fsa_Input_DateOfBirthDay",
      "field_type": "number",
      "interaction": "fill"
    },
    {
      "field_id": "year",
      "selector": "#fsa_Input_DateOfBirthYear",
      "field_type": "number",
      "interaction": "fill"
    }
  ]
}
```

---

### Pattern 5: Clicking Label/Button Area (Not Input)

**Problem:** Actual input element may be hidden, but clickable area exists

**FSA Example:**
```html
<div id="fsa_Radio_ButtonMaritalStatusUnmarried" 
     class="fsa-radio-label fsa-radio-button-card-label">
  Unmarried (single, divorced, or widowed)
</div>
<input type="radio" 
       id="fsa_Radio_MaritalStatusUnmarried" 
       style="display: none">
```

**Solution:** Click the visible label div, not the hidden input

```python
# Option A: Click by label div ID
await page.locator('#fsa_Radio_ButtonMaritalStatusUnmarried').click()

# Option B: Click by text (if unique)
await page.locator('text=Unmarried (single, divorced, or widowed)').first.click()

# Option C: JavaScript on hidden input (most reliable)
await page.evaluate('document.getElementById("fsa_Radio_MaritalStatusUnmarried").click()')
```

**Recommended:** Option C (JavaScript) - most reliable across browsers

---

### Pattern 6: Full-Page Screenshots

**Problem:** Forms have content below the fold that's not visible in viewport

**Solution:** Use `full_page=True` for screenshots

```python
# ❌ Only captures viewport (visible area)
screenshot = await page.screenshot()

# ✅ Captures entire page including scrolled content
screenshot = await page.screenshot(full_page=True)
```

**Optimization:**
```python
# Optimize for size
screenshot = await page.screenshot(
    full_page=True,
    type='jpeg',
    quality=80  # 80% quality for good balance
)
```

**Target size:** <100KB per screenshot for fast MCP transport

---

### Pattern 7: Handling Duplicate Selectors

**Problem:** Same text appears multiple times (visible + screen reader)

**FSA Example:**
```html
<span class="sr-only">First year (freshman)</span>
<div class="fsa-radio-label">First year (freshman)</div>
```

**Error:**
```
strict mode violation: locator("text=First year (freshman)") 
resolved to 2 elements
```

**Solution:** Use unique ID instead of text

```python
# ❌ This fails - matches 2 elements
await page.locator('text=First year (freshman)').click()

# ✅ Use specific ID
await page.locator('#fsa_Radio_ButtonCollegeLevelFreshman').click()

# Or wait for the specific element
await page.wait_for_selector('#fsa_Radio_CollegeLevelFreshman', state='attached')
```

**Priority for selectors:**
1. Unique ID (best)
2. Unique name attribute
3. CSS class + specific context
4. Text content (only if unique)

---

### Pattern 8: Navigation and Load Waiting

**Problem:** Pages take time to load, especially government sites

**Solution:** Always wait for networkidle after navigation

```python
# After clicking links/buttons
await page.click('button:has-text("Continue")')
await page.wait_for_load_state('networkidle')  # Wait for network to settle

# After page.goto()
await page.goto(url)
await page.wait_for_load_state('networkidle')

# For AJAX-heavy pages, also wait for specific elements
await page.wait_for_load_state('networkidle')
await page.wait_for_selector('#main-content')
```

**Load states:**
- `load` - Page load event fired
- `domcontentloaded` - DOM is ready
- `networkidle` - No network connections for 500ms (recommended)

---

## Complete FSA Page 1 Example

**Reference:** `requirements/reference/fsa-test-results/test_basic_navigation.py`

```python
async def fill_fsa_page1(page):
    """
    Complete working example from FSA testing
    Demonstrates all key patterns
    """
    
    # Navigate to FSA
    await page.goto('https://studentaid.gov/aid-estimator/')
    await page.wait_for_load_state('networkidle')
    
    # Click Start Estimate
    await page.locator('text=Start Estimate').first.click()
    await page.wait_for_load_state('networkidle')
    
    # Wait for form to be ready
    await page.wait_for_selector('#fsa_Input_DateOfBirthMonth', timeout=10000)
    
    # Pattern 4: Number inputs for birthdate
    await page.fill('#fsa_Input_DateOfBirthMonth', '05')
    await page.fill('#fsa_Input_DateOfBirthDay', '15')
    await page.fill('#fsa_Input_DateOfBirthYear', '2007')
    
    # Pattern 1: Hidden radio button - use JavaScript
    await page.locator('#fsa_Radio_ButtonMaritalStatusUnmarried').click()
    
    # Pattern 2: Typeahead field
    await page.fill('#fsa_Typeahead_StateOfResidence', 'Illinois')
    await page.wait_for_timeout(500)
    await page.keyboard.press('Enter')
    
    # Pattern 3: Wait for dynamic element (hidden)
    await page.wait_for_selector('#fsa_Radio_CollegeLevelFreshman', 
                                 state='attached', 
                                 timeout=10000)
    await page.wait_for_timeout(500)
    
    # Pattern 1: JavaScript click for hidden radio
    await page.evaluate('document.querySelector("#fsa_Radio_CollegeLevelFreshman").click()')
    
    # Pattern 6: Full-page screenshot
    screenshot = await page.screenshot(full_page=True, type='jpeg', quality=80)
    
    # Pattern 8: Navigate to next page
    await page.locator('button:has-text("Continue")').first.click()
    await page.wait_for_load_state('networkidle')
    
    return screenshot
```

---

## Field Type Detection Rules

**During discovery, classify fields as:**

```python
def detect_field_type(element):
    """
    Determine field type from HTML element
    """
    tag_name = element.tag_name
    element_type = element.get_attribute('type')
    element_id = element.get_attribute('id') or ''
    element_class = element.get_attribute('class') or ''
    
    # Number inputs
    if tag_name == 'input' and element_type == 'number':
        return 'number', 'fill'
    
    # Text inputs
    if tag_name == 'input' and element_type in ['text', 'email', 'tel']:
        return 'text', 'fill'
    
    # Hidden radio/checkbox - needs JavaScript
    if tag_name == 'input' and element_type in ['radio', 'checkbox']:
        is_visible = element.is_visible()
        if not is_visible:
            return element_type, 'javascript_click'
        return element_type, 'click'
    
    # Typeahead/autocomplete
    if tag_name == 'input' and element_type == 'search':
        return 'typeahead', 'fill_enter'
    
    if 'typeahead' in element_id.lower() or 'typeahead' in element_class.lower():
        return 'typeahead', 'fill_enter'
    
    # Select dropdowns
    if tag_name == 'select':
        return 'select', 'select'
    
    # Textarea
    if tag_name == 'textarea':
        return 'textarea', 'fill'
    
    return 'unknown', 'fill'  # Default
```

---

## Error Recovery Patterns

### Selector Not Found

```python
async def click_with_retry(page, selectors, max_retries=3):
    """
    Try multiple selector strategies
    """
    for selector in selectors:
        try:
            await page.locator(selector).click(timeout=5000)
            return True
        except Exception as e:
            continue
    
    return False  # All selectors failed

# Usage
success = await click_with_retry(page, [
    '#exact_id',
    '.class-name',
    'text=Button Text'
])
```

### Element Not Interactable

```python
async def force_click(page, selector):
    """
    Use JavaScript if normal click fails
    """
    try:
        await page.click(selector, timeout=5000)
    except Exception:
        # Fall back to JavaScript
        selector_id = selector.replace('#', '')
        await page.evaluate(f'document.getElementById("{selector_id}").click()')
```

---

## Best Practices Summary

### ✅ DO:
- Use IDs for selectors (most reliable)
- Wait for `networkidle` after navigation
- Use `state='attached'` for hidden elements
- Take full-page screenshots
- Use JavaScript click for hidden inputs
- Add small delays (500ms) after typeahead input
- Test selectors during discovery

### ❌ DON'T:
- Assume elements are visible
- Use text selectors if IDs available
- Skip wait times after navigation
- Trust that selectors will work in production
- Forget to handle loading states
- Use viewport-only screenshots

---

## Testing Your Patterns

```python
async def test_field_interaction(page, field_metadata):
    """
    Test a field interaction based on discovered metadata
    """
    selector = field_metadata['selector']
    interaction = field_metadata['interaction']
    test_value = field_metadata['example_value']
    
    try:
        if interaction == 'fill':
            await page.fill(selector, test_value)
            
        elif interaction == 'fill_enter':
            await page.fill(selector, test_value)
            await page.wait_for_timeout(500)
            await page.keyboard.press('Enter')
            
        elif interaction == 'javascript_click':
            selector_id = selector.replace('#', '')
            await page.evaluate(f'document.getElementById("{selector_id}").click()')
            
        elif interaction == 'click':
            await page.click(selector)
            
        elif interaction == 'select':
            await page.select_option(selector, test_value)
        
        # Verify it worked
        await page.wait_for_timeout(500)
        screenshot = await page.screenshot()
        
        return {
            'success': True,
            'screenshot': screenshot
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'screenshot': await page.screenshot()
        }
```

---

## References

- Working FSA Test: `requirements/reference/fsa-test-results/test_basic_navigation.py`
- Playwright Docs: https://playwright.dev/python/docs/api/class-page
- FSA Wizard Structure: `wizards/fsa-estimator.json` (to be created)