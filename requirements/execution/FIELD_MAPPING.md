# Field Mapping Requirements

## Purpose

Define how to map natural language user data to wizard field selectors during execution.

---

## Core Challenge

**User provides natural language:**
```
"My family income is $85k, we're a family of 4, 
 I'm 18 years old, born in 2007, live in Illinois"
```

**Wizard needs structured data:**
```python
{
    "#fsa_Input_DateOfBirthYear": "2007",
    "#parent_income": "85000",  # Note: cleaned from "$85k"
    "#family_size": "4",
    "#fsa_Typeahead_StateOfResidence": "Illinois"
}
```

---

## Requirements

### REQ-FM-001: Flexible Input Parsing

**Must handle various user input formats:**

**Currency:**
- "$85,000" → "85000"
- "$85k" → "85000"
- "85K" → "85000"
- "85000" → "85000"

**Numbers:**
- "1,234" → "1234"
- "1.5k" → "1500"
- "four" → "4" (text numbers)

**Dates:**
- "2007" → year field
- "May 15, 2007" → parse into month, day, year
- "05/15/2007" → parse components

**States:**
- "IL" → "Illinois"
- "illinois" → "Illinois" (capitalize)
- "California" → "California"

**Boolean/Options:**
- "yes" → "Yes" or true or specific selector
- "married" → "Married / Re-married" (match wizard option)
- "freshman" → "First year (freshman)" (fuzzy match)

---

### REQ-FM-002: Label-Based Matching

**Match user data to fields by label similarity:**

```python
wizard_field_labels = [
    "What is the student's date of birth?",
    "What is the student's state of legal residence?",
    "What is the parent's income?",
    "How many people are in the family?"
]

user_data = {
    "birth_year": "2007",
    "state": "Illinois",
    "income": "85000",
    "family_size": "4"
}

# Mapper should match:
"birth_year" → "What is the student's date of birth?" → #fsa_Input_DateOfBirthYear
"state" → "What is the student's state of legal residence?" → #fsa_Typeahead_StateOfResidence
"income" → "What is the parent's income?" → #parent_income
"family_size" → "How many people are in the family?" → #family_size
```

**Matching strategies:**
- Exact keyword match ("income" matches "income")
- Fuzzy match with Levenshtein distance
- Synonym mapping ("dob" → "date of birth")
- Context from field_id in JSON

---

### REQ-FM-003: Required Field Validation

**Before execution, validate all required fields have values:**

```python
def validate_user_data(user_data, wizard_structure):
    """
    Check if user provided all required fields
    """
    required_fields = []
    
    for page in wizard_structure['pages']:
        for field in page['fields']:
            if field.get('required', False):
                required_fields.append(field)
    
    missing = []
    for field in required_fields:
        if not find_user_value(user_data, field):
            missing.append({
                'label': field['label'],
                'field_id': field['field_id'],
                'example': field.get('example_value')
            })
    
    return {
        'valid': len(missing) == 0,
        'missing_fields': missing
    }
```

**If fields missing, return to Claude:**
```python
{
    'status': 'missing_data',
    'missing_fields': [
        {
            'label': 'What is the student\'s date of birth?',
            'example': '2007'
        }
    ]
}
```

**Claude asks user for missing data before executing.**

---

### REQ-FM-004: Sensible Defaults

**Provide defaults for non-critical optional fields:**

```python
DEFAULT_VALUES = {
    'student_assets': '0',  # Most students have no assets
    'student_income': '0',  # Most students have no income
    'birth_month': '01',    # If not provided
    'birth_day': '01',      # If not provided
}
```

**Only for truly optional fields where default won't affect result significantly.**

---

## Field Mapper Implementation

### Core Interface

```python
class FieldMapper:
    """
    Maps user data to wizard field values
    """
    
    def map_user_data(self, 
                      user_data: dict, 
                      wizard_structure: dict) -> dict:
        """
        Map user data to field selectors
        
        Args:
            user_data: Natural language user data
            wizard_structure: Loaded wizard JSON
            
        Returns:
            {
                selector: value,
                ...
            }
        """
        pass
    
    def validate_completeness(self, 
                             user_data: dict, 
                             wizard_structure: dict) -> dict:
        """
        Check if user data is complete
        
        Returns:
            {
                'valid': bool,
                'missing_fields': [...],
                'suggestions': [...]
            }
        """
        pass
    
    def clean_value(self, 
                   value: str, 
                   field_type: str) -> str:
        """
        Clean and format value for field type
        
        Args:
            value: Raw user input
            field_type: 'currency', 'number', 'date', 'text', etc.
            
        Returns:
            Cleaned value
        """
        pass
```

---

### Data Cleaning Functions

```python
def clean_currency(value: str) -> str:
    """
    Clean currency input
    
    Examples:
        "$85,000" → "85000"
        "$85k" → "85000"
        "85K" → "85000"
    """
    value = value.replace('$', '').replace(',', '')
    value = value.lower()
    
    if value.endswith('k'):
        value = value[:-1]
        return str(int(float(value) * 1000))
    
    return value

def clean_number(value: str) -> str:
    """
    Clean numeric input
    
    Examples:
        "1,234" → "1234"
        "1.5k" → "1500"
    """
    value = value.replace(',', '')
    
    if value.lower().endswith('k'):
        return str(int(float(value[:-1]) * 1000))
    
    return value

def normalize_state(value: str) -> str:
    """
    Normalize state names
    
    Examples:
        "IL" → "Illinois"
        "california" → "California"
        "TEXAS" → "Texas"
    """
    STATE_ABBREVIATIONS = {
        'AL': 'Alabama', 'AK': 'Alaska', 'AZ': 'Arizona',
        'IL': 'Illinois', 'CA': 'California', 'TX': 'Texas',
        # ... full mapping
    }
    
    value = value.strip()
    
    # Check if abbreviation
    if len(value) == 2:
        return STATE_ABBREVIATIONS.get(value.upper(), value)
    
    # Capitalize properly
    return value.title()

def parse_date(value: str) -> dict:
    """
    Parse various date formats
    
    Examples:
        "2007" → {'year': '2007'}
        "05/15/2007" → {'month': '05', 'day': '15', 'year': '2007'}
        "May 15, 2007" → {'month': '05', 'day': '15', 'year': '2007'}
    """
    from dateutil import parser
    
    try:
        dt = parser.parse(value)
        return {
            'year': str(dt.year),
            'month': str(dt.month).zfill(2),
            'day': str(dt.day).zfill(2)
        }
    except:
        # Might just be a year
        if value.isdigit() and len(value) == 4:
            return {'year': value}
        return {}
```

---

### Label Matching

```python
def match_field_label(user_key: str, field_labels: list) -> str:
    """
    Match user data key to wizard field label
    
    Uses fuzzy matching and synonyms
    """
    from fuzzywuzzy import fuzz
    
    # Synonym mapping
    SYNONYMS = {
        'dob': 'date of birth',
        'birthday': 'date of birth',
        'income': 'income',
        'salary': 'income',
        'earnings': 'income',
        'state': 'state of residence',
        'family': 'family size',
        'household': 'family size',
    }
    
    # Expand user key with synonyms
    search_terms = [user_key.lower()]
    if user_key.lower() in SYNONYMS:
        search_terms.append(SYNONYMS[user_key.lower()])
    
    best_match = None
    best_score = 0
    
    for field_label in field_labels:
        label_lower = field_label.lower()
        
        for term in search_terms:
            # Exact substring match
            if term in label_lower:
                return field_label
            
            # Fuzzy match
            score = fuzz.partial_ratio(term, label_lower)
            if score > best_score:
                best_score = score
                best_match = field_label
    
    # Only return if confidence is high
    if best_score > 70:
        return best_match
    
    return None
```

---

### Complete Example

```python
# User provides natural language data
user_data = {
    "birth_year": "2007",
    "student_unmarried": True,
    "state": "IL",
    "grade": "freshman",
    "parent_married": "yes",
    "family_size": "4",
    "parent_income": "$85k",
    "parent_assets": "$12,000",
    "student_income": None,  # Not provided
    "student_assets": None   # Not provided
}

# Load wizard structure
wizard = load_json("wizards/fsa-estimator.json")

# Map user data
mapper = FieldMapper()
field_values = mapper.map_user_data(user_data, wizard)

# Result:
{
    "#fsa_Input_DateOfBirthMonth": "01",  # Default
    "#fsa_Input_DateOfBirthDay": "01",    # Default
    "#fsa_Input_DateOfBirthYear": "2007",
    "#fsa_Radio_MaritalStatusUnmarried": True,  # Click it
    "#fsa_Typeahead_StateOfResidence": "Illinois",  # IL → Illinois
    "#fsa_Radio_CollegeLevelFreshman": True,  # "freshman" matched
    "#parent_marital_status_married": True,
    "#family_size": "4",
    "#parent_income": "85000",  # Cleaned from $85k
    "#parent_assets": "12000",  # Cleaned from $12,000
    "#student_income": "0",     # Default
    "#student_assets": "0"      # Default
}
```

---

## Error Handling

### REQ-FM-005: Ambiguous Matches

**If field mapper can't confidently match user data to field:**

```python
{
    'status': 'ambiguous',
    'field_label': 'What is the parent\'s income?',
    'possible_matches': [
        'parent_income',
        'parent_salary',
        'parent_earnings'
    ],
    'clarification_needed': 'Which value did you mean for parent income?'
}
```

**Claude asks user for clarification.**

---

### REQ-FM-006: Invalid Data Types

**If value doesn't match expected type:**

```python
# User provides "abc" for income field
{
    'status': 'invalid_type',
    'field_label': 'Parent income',
    'expected_type': 'currency',
    'provided_value': 'abc',
    'error': 'Income must be a number or currency amount'
}
```

---

### REQ-FM-007: Out of Range Values

**If value is unrealistic:**

```python
# Income over $1M might be unusual
# Birth year before 1900 is invalid
# Family size over 20 is suspicious

def validate_range(field_id, value):
    RANGES = {
        'income': (0, 1000000),
        'birth_year': (1900, 2025),
        'family_size': (1, 20)
    }
    
    if field_id in RANGES:
        min_val, max_val = RANGES[field_id]
        val = int(value)
        
        if val < min_val or val > max_val:
            return {
                'valid': False,
                'message': f'{field_id} should be between {min_val} and {max_val}'
            }
    
    return {'valid': True}
```

---

## Testing Requirements

### Unit Tests

```python
def test_clean_currency():
    assert clean_currency("$85,000") == "85000"
    assert clean_currency("$85k") == "85000"
    assert clean_currency("85K") == "85000"

def test_normalize_state():
    assert normalize_state("IL") == "Illinois"
    assert normalize_state("california") == "California"

def test_parse_date():
    result = parse_date("05/15/2007")
    assert result['month'] == "05"
    assert result['day'] == "15"
    assert result['year'] == "2007"

def test_match_field_label():
    labels = [
        "What is the student's date of birth?",
        "What is the parent's income?"
    ]
    assert match_field_label("dob", labels) == labels[0]
    assert match_field_label("income", labels) == labels[1]
```

### Integration Test

```python
def test_complete_fsa_mapping():
    """Test mapping for complete FSA workflow"""
    user_data = {
        "birth_year": "2007",
        "state": "IL",
        "income": "$85k",
        "family_size": "4"
    }
    
    wizard = load_json("wizards/fsa-estimator.json")
    mapper = FieldMapper()
    
    field_values = mapper.map_user_data(user_data, wizard)
    
    # Verify all pages have mappings
    for page in wizard['pages']:
        for field in page['fields']:
            if field.get('required'):
                assert field['selector'] in field_values
```

---

## Success Criteria

Field mapper is successful when:
1. ✅ Handles common input formats (currency, numbers, dates, states)
2. ✅ Matches user data keys to wizard field labels with >90% accuracy
3. ✅ Validates required fields are present
4. ✅ Provides helpful error messages for missing/invalid data
5. ✅ Applies sensible defaults appropriately
6. ✅ Handles ambiguous cases by asking for clarification
7. ✅ All unit tests pass
8. ✅ Complete FSA mapping test passes

---

## References

- FSA Wizard Structure: `wizards/fsa-estimator.json`
- Execution Requirements: `requirements/execution/EXECUTION_REQUIREMENTS.md`
- Wizard Schema: `requirements/shared/WIZARD_STRUCTURE_SCHEMA.md`