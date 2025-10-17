"""
FederalScout Discovery Agent - MCP server for wizard structure discovery.

This package provides interactive wizard structure discovery through
Claude Desktop using Model Context Protocol (MCP).
"""

__version__ = "1.0.0"

from config import get_config, FederalScoutConfig
from models import WizardStructure, PageStructure, FieldStructure
from logging_config import get_logger

__all__ = [
    "get_config",
    "FederalScoutConfig",
    "WizardStructure",
    "PageStructure",
    "FieldStructure",
    "get_logger"
]
