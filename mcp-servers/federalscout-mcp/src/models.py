"""
Shared Pydantic models for wizard structure.

These models define the canonical JSON structure for representing discovered
government form wizards. They provide type safety, validation, and
serialization/deserialization for wizard structures.

Reference: requirements/shared/WIZARD_STRUCTURE_SCHEMA.md
"""

from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field, field_validator, model_validator


class SelectorType(str, Enum):
    """Types of selectors used to locate elements."""
    TEXT = "text"
    ID = "id"
    CSS = "css"
    AUTO = "auto"


class FieldType(str, Enum):
    """Types of form fields in wizards."""
    TEXT = "text"
    NUMBER = "number"
    RADIO = "radio"
    SELECT = "select"
    TYPEAHEAD = "typeahead"
    CHECKBOX = "checkbox"
    GROUP = "group"
    TEXTAREA = "textarea"
    SEARCH = "search"


class InteractionType(str, Enum):
    """Methods for interacting with form fields."""
    FILL = "fill"
    CLICK = "click"
    SELECT = "select"
    JAVASCRIPT_CLICK = "javascript_click"
    FILL_ENTER = "fill_enter"


class SubFieldStructure(BaseModel):
    """Structure for sub-fields within a grouped field (e.g., date components)."""
    field_id: str = Field(..., description="Unique identifier within the group")
    selector: str = Field(..., description="CSS selector for the sub-field")
    field_type: FieldType = Field(..., description="Type of the sub-field")
    interaction: InteractionType = Field(..., description="How to interact with this sub-field")
    example_value: str = Field(..., description="Example value for testing")
    notes: Optional[str] = Field(None, description="Additional notes about this sub-field")

    @field_validator('selector')
    @classmethod
    def validate_selector(cls, v: str) -> str:
        """Ensure selector is not empty."""
        if not v or not v.strip():
            raise ValueError("Selector cannot be empty")
        return v.strip()


class FieldStructure(BaseModel):
    """Structure for a single form field."""
    label: str = Field(..., description="Human-readable label as shown to user")
    field_id: str = Field(..., description="Unique identifier within the wizard")
    selector: str = Field(..., description="Primary CSS selector for the field")
    selector_alternatives: Optional[List[str]] = Field(
        default=None,
        description="Alternative selectors if primary fails"
    )
    field_type: FieldType = Field(..., description="Type of form field")
    interaction: InteractionType = Field(..., description="Method for interacting with field")
    required: bool = Field(default=False, description="Whether field is required")
    example_value: Union[str, Dict[str, Any]] = Field(
        ...,
        description="Example value for testing (string or object for grouped fields)"
    )
    notes: Optional[str] = Field(None, description="Special handling instructions")
    sub_fields: Optional[List[SubFieldStructure]] = Field(
        default=None,
        description="Sub-fields for grouped fields (e.g., date components)"
    )

    @field_validator('selector')
    @classmethod
    def validate_selector(cls, v: str) -> str:
        """Ensure selector is not empty."""
        if not v or not v.strip():
            raise ValueError("Selector cannot be empty")
        return v.strip()

    @field_validator('field_id')
    @classmethod
    def validate_field_id(cls, v: str) -> str:
        """Ensure field_id is not empty and follows conventions."""
        if not v or not v.strip():
            raise ValueError("Field ID cannot be empty")
        return v.strip()

    @model_validator(mode='after')
    def validate_group_fields(self):
        """Ensure grouped fields have sub_fields defined."""
        if self.field_type == FieldType.GROUP:
            if not self.sub_fields or len(self.sub_fields) == 0:
                raise ValueError("Grouped fields must have at least one sub_field")
        return self


class ContinueButton(BaseModel):
    """Structure for the continue/next button on a page."""
    text: str = Field(..., description="Button text (e.g., 'Continue', 'Next')")
    selector: str = Field(..., description="CSS selector for the button")
    selector_type: Optional[SelectorType] = Field(
        default=SelectorType.CSS,
        description="Type of selector"
    )

    @field_validator('selector')
    @classmethod
    def validate_selector(cls, v: str) -> str:
        """Ensure selector is not empty."""
        if not v or not v.strip():
            raise ValueError("Selector cannot be empty")
        return v.strip()


class ValidationRules(BaseModel):
    """Validation rules for a page."""
    error_selector: Optional[str] = Field(
        None,
        description="CSS selector for error messages"
    )
    required_fields: Optional[List[str]] = Field(
        default=None,
        description="List of field_ids that are required on this page"
    )


class PageStructure(BaseModel):
    """Structure for a single page in the wizard."""
    page_number: int = Field(..., ge=1, description="Page number (1-indexed)")
    page_title: str = Field(..., description="Title or heading of the page")
    url_pattern: Optional[str] = Field(None, description="URL pattern after navigation")
    fields: List[FieldStructure] = Field(
        default_factory=list,
        description="List of fields on this page"
    )
    continue_button: ContinueButton = Field(..., description="Continue/Next button")
    validation: Optional[ValidationRules] = Field(
        default=None,
        description="Validation rules for this page"
    )

    @field_validator('page_title')
    @classmethod
    def validate_page_title(cls, v: str) -> str:
        """Ensure page title is not empty."""
        if not v or not v.strip():
            raise ValueError("Page title cannot be empty")
        return v.strip()


class StartAction(BaseModel):
    """Action to start the wizard (e.g., clicking a button)."""
    description: str = Field(..., description="Description of the action to start")
    selector: str = Field(..., description="CSS selector for the start element")
    selector_type: SelectorType = Field(
        default=SelectorType.TEXT,
        description="Type of selector"
    )

    @field_validator('selector')
    @classmethod
    def validate_selector(cls, v: str) -> str:
        """Ensure selector is not empty."""
        if not v or not v.strip():
            raise ValueError("Selector cannot be empty")
        return v.strip()


class WizardStructure(BaseModel):
    """Complete structure for a wizard."""
    wizard_id: str = Field(
        ...,
        pattern=r'^[a-z0-9-]+$',
        description="Unique identifier (lowercase, hyphens only)"
    )
    name: str = Field(..., description="Human-readable display name")
    url: str = Field(..., description="Starting URL of the wizard")
    discovered_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When this wizard was discovered"
    )
    discovery_version: str = Field(
        default="1.0.0",
        description="Version of FederalScout used for discovery"
    )
    total_pages: int = Field(..., ge=1, description="Total number of pages in wizard")
    start_action: Optional[StartAction] = Field(
        None,
        description="Action required to start the wizard"
    )
    pages: List[PageStructure] = Field(
        default_factory=list,
        description="List of pages in the wizard"
    )

    @field_validator('url')
    @classmethod
    def validate_url(cls, v: str) -> str:
        """Ensure URL is valid."""
        if not v or not v.strip():
            raise ValueError("URL cannot be empty")
        if not v.startswith(('http://', 'https://')):
            raise ValueError("URL must start with http:// or https://")
        return v.strip()

    @model_validator(mode='after')
    def validate_pages_count(self):
        """Ensure pages list matches total_pages."""
        if len(self.pages) != self.total_pages:
            raise ValueError(
                f"total_pages ({self.total_pages}) does not match "
                f"actual page count ({len(self.pages)})"
            )
        return self

    @model_validator(mode='after')
    def validate_page_numbers(self):
        """Ensure page numbers are sequential starting from 1."""
        if not self.pages:
            return self

        page_numbers = sorted([page.page_number for page in self.pages])
        expected = list(range(1, len(self.pages) + 1))

        if page_numbers != expected:
            raise ValueError(
                f"Page numbers must be sequential starting from 1. "
                f"Found: {page_numbers}, Expected: {expected}"
            )
        return self

    def to_json_file(self, output_dir: Path) -> Path:
        """
        Save wizard structure to JSON file.

        Args:
            output_dir: Directory to save the file

        Returns:
            Path to the saved file
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        filename = f"{self.wizard_id}.json"
        filepath = output_dir / filename

        with open(filepath, 'w') as f:
            f.write(self.model_dump_json(indent=2, exclude_none=True))

        return filepath

    @classmethod
    def from_json_file(cls, filepath: Path) -> 'WizardStructure':
        """
        Load wizard structure from JSON file.

        Args:
            filepath: Path to the JSON file

        Returns:
            WizardStructure instance
        """
        with open(filepath, 'r') as f:
            data = f.read()

        return cls.model_validate_json(data)

    def get_all_required_fields(self) -> List[FieldStructure]:
        """
        Get all required fields across all pages.

        Returns:
            List of required FieldStructure objects
        """
        required_fields = []
        for page in self.pages:
            for field in page.fields:
                if field.required:
                    required_fields.append(field)
        return required_fields

    def get_field_by_id(self, field_id: str) -> Optional[FieldStructure]:
        """
        Find a field by its field_id.

        Args:
            field_id: The field identifier to search for

        Returns:
            FieldStructure if found, None otherwise
        """
        for page in self.pages:
            for field in page.fields:
                if field.field_id == field_id:
                    return field
        return None

    def get_page_by_number(self, page_number: int) -> Optional[PageStructure]:
        """
        Get a page by its page number.

        Args:
            page_number: The page number (1-indexed)

        Returns:
            PageStructure if found, None otherwise
        """
        for page in self.pages:
            if page.page_number == page_number:
                return page
        return None

    def validate_completeness(self) -> Dict[str, Any]:
        """
        Validate that the wizard structure is complete and usable.

        Returns:
            Dictionary with validation results
        """
        warnings = []
        errors = []

        # Check if at least one page exists
        if not self.pages:
            errors.append("No pages defined in wizard")

        # Check each page
        for page in self.pages:
            # Check if page has fields
            if not page.fields:
                warnings.append(f"Page {page.page_number} has no fields defined")

            # Check if required fields have selectors
            for field in page.fields:
                if not field.selector:
                    errors.append(
                        f"Field '{field.label}' on page {page.page_number} "
                        f"has no selector"
                    )

                # Check grouped fields
                if field.field_type == FieldType.GROUP:
                    if not field.sub_fields:
                        errors.append(
                            f"Grouped field '{field.label}' on page {page.page_number} "
                            f"has no sub_fields"
                        )

        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings,
            'total_pages': self.total_pages,
            'total_fields': sum(len(page.fields) for page in self.pages),
            'required_fields_count': len(self.get_all_required_fields())
        }


# Utility functions for validation

def validate_wizard_json(json_data: str) -> Dict[str, Any]:
    """
    Validate wizard JSON structure.

    Args:
        json_data: JSON string to validate

    Returns:
        Dictionary with validation results
    """
    try:
        wizard = WizardStructure.model_validate_json(json_data)
        completeness = wizard.validate_completeness()

        return {
            'valid': True,
            'wizard': wizard,
            'completeness': completeness
        }
    except Exception as e:
        return {
            'valid': False,
            'error': str(e),
            'error_type': type(e).__name__
        }


def load_wizard(filepath: Path) -> WizardStructure:
    """
    Load and validate a wizard structure from file.

    Args:
        filepath: Path to the wizard JSON file

    Returns:
        Validated WizardStructure instance

    Raises:
        ValueError: If the file doesn't exist or is invalid
    """
    if not filepath.exists():
        raise ValueError(f"Wizard file not found: {filepath}")

    try:
        return WizardStructure.from_json_file(filepath)
    except Exception as e:
        raise ValueError(f"Invalid wizard structure in {filepath}: {e}")


def save_wizard(wizard: WizardStructure, output_dir: Path) -> Path:
    """
    Save a wizard structure to file.

    Args:
        wizard: WizardStructure instance to save
        output_dir: Directory to save the file

    Returns:
        Path to the saved file
    """
    return wizard.to_json_file(output_dir)
