"""
FederalScout MCP Server - stdio transport for Claude Desktop.

Implements MCP protocol with stdio transport to enable interactive
wizard structure discovery through Claude Desktop conversations.

Reference: requirements/discovery/DISCOVERY_REQUIREMENTS.md REQ-DISC-001
"""

import asyncio
import sys
from typing import Any, Callable

from mcp.server import Server
from mcp.types import Tool, TextContent, ImageContent

from config import get_config
from logging_config import get_logger, setup_logging
from discovery_tools import (
    federalscout_start_discovery,
    federalscout_click_element,
    federalscout_execute_actions,
    federalscout_get_page_info,
    federalscout_save_page_metadata,
    federalscout_complete_discovery,
    federalscout_save_schema
)


# Initialize logging (to file, not stdout)
logger = get_logger('federalscout.server')
logger.info("FederalScout MCP Server starting...")


# Create MCP server instance
server = Server("federalscout")


# Tool definitions for MCP
TOOL_DEFINITIONS = [
    Tool(
        name="federalscout_start_discovery",
        description="Begin wizard structure discovery session. Launches browser, navigates to URL, and returns screenshot with HTML context.",
        inputSchema={
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "Starting URL of the government wizard (e.g., https://studentaid.gov/aid-estimator/)"
                }
            },
            "required": ["url"]
        }
    ),
    Tool(
        name="federalscout_click_element",
        description="Click an element on the current page. Returns screenshot and updated HTML context after click.",
        inputSchema={
            "type": "object",
            "properties": {
                "session_id": {
                    "type": "string",
                    "description": "Session ID from start_discovery"
                },
                "selector": {
                    "type": "string",
                    "description": "CSS selector or text to click (e.g., '#button_id', '.class-name', or 'Start Estimate')"
                },
                "selector_type": {
                    "type": "string",
                    "enum": ["text", "id", "css", "auto"],
                    "default": "auto",
                    "description": "How to interpret the selector"
                }
            },
            "required": ["session_id", "selector"]
        }
    ),
    Tool(
        name="federalscout_execute_actions",
        description="Execute multiple DIVERSE actions (fill, click, etc.) in one call (UNIVERSAL BATCH). The most powerful batch tool - drastically reduces conversation size by handling any combination of actions. Takes screenshot AFTER all actions complete. Use this when you need to combine clicks and fills in sequence.",
        inputSchema={
            "type": "object",
            "properties": {
                "session_id": {
                    "type": "string",
                    "description": "Session ID from start_discovery"
                },
                "actions": {
                    "type": "array",
                    "description": "Array of actions to execute in sequence (fill, click, fill_enter, javascript_click, select)",
                    "items": {
                        "type": "object",
                        "properties": {
                            "action": {
                                "type": "string",
                                "enum": ["fill", "fill_enter", "click", "javascript_click", "select"],
                                "description": "Type of action to perform"
                            },
                            "selector": {
                                "type": "string",
                                "description": "CSS selector or text for the element"
                            },
                            "value": {
                                "type": "string",
                                "description": "Value to fill (required for fill/fill_enter/select, optional for click)"
                            },
                            "selector_type": {
                                "type": "string",
                                "enum": ["text", "id", "css", "auto"],
                                "default": "auto",
                                "description": "How to interpret the selector (for click actions)"
                            }
                        },
                        "required": ["action", "selector"]
                    }
                }
            },
            "required": ["session_id", "actions"]
        }
    ),
    Tool(
        name="federalscout_get_page_info",
        description="Get detailed information about the current page including all form elements, buttons, and metadata. Returns element data WITHOUT screenshot to reduce conversation size. Use start_discovery, click_element, or execute_actions for screenshots.",
        inputSchema={
            "type": "object",
            "properties": {
                "session_id": {
                    "type": "string",
                    "description": "Session ID from start_discovery"
                }
            },
            "required": ["session_id"]
        }
    ),
    Tool(
        name="federalscout_save_page_metadata",
        description="Save discovered page structure to the session. Call this after fully discovering a page's fields and continue button.",
        inputSchema={
            "type": "object",
            "properties": {
                "session_id": {
                    "type": "string",
                    "description": "Session ID from start_discovery"
                },
                "page_metadata": {
                    "type": "object",
                    "description": "Page structure with fields, continue button, etc.",
                    "properties": {
                        "page_number": {"type": "integer", "minimum": 1},
                        "page_title": {"type": "string"},
                        "url_pattern": {"type": "string"},
                        "fields": {"type": "array"},
                        "continue_button": {"type": "object"}
                    },
                    "required": ["page_number", "page_title", "fields", "continue_button"]
                }
            },
            "required": ["session_id", "page_metadata"]
        }
    ),
    Tool(
        name="federalscout_complete_discovery",
        description="Complete discovery and save wizard structure to JSON file. Validates against Universal Schema. Returns the complete wizard JSON structure for the agent to create an artifact. Closes browser and cleans up session. IMPORTANT: After this succeeds, you MUST call federalscout_save_schema to generate the User Data Schema (Contract-First pattern).",
        inputSchema={
            "type": "object",
            "properties": {
                "session_id": {
                    "type": "string",
                    "description": "Session ID from start_discovery"
                },
                "wizard_name": {
                    "type": "string",
                    "description": "Human-readable name (e.g., 'FSA Student Aid Estimator')"
                },
                "wizard_id": {
                    "type": "string",
                    "pattern": "^[a-z0-9-]+$",
                    "description": "Filename slug (lowercase, hyphens only, e.g., 'fsa-estimator')"
                },
                "start_action": {
                    "type": "object",
                    "description": "Optional: Action required to start wizard",
                    "properties": {
                        "description": {"type": "string"},
                        "selector": {"type": "string"},
                        "selector_type": {"type": "string"}
                    }
                }
            },
            "required": ["session_id", "wizard_name", "wizard_id"]
        }
    ),
    Tool(
        name="federalscout_save_schema",
        description="Save User Data Schema that defines THE CONTRACT for this wizard. MUST be called immediately after federalscout_complete_discovery. The schema defines what user data FederalRunner needs to collect. Property names MUST match field_id values from discovered wizard structure.",
        inputSchema={
            "type": "object",
            "properties": {
                "wizard_id": {
                    "type": "string",
                    "pattern": "^[a-z0-9-]+$",
                    "description": "Wizard identifier (must match wizard just discovered)"
                },
                "schema_content": {
                    "type": "object",
                    "description": "Complete JSON Schema (draft-07) defining required user data",
                    "properties": {
                        "$schema": {
                            "type": "string",
                            "description": "Must be 'http://json-schema.org/draft-07/schema#'"
                        },
                        "title": {"type": "string"},
                        "description": {"type": "string"},
                        "type": {"type": "string"},
                        "required": {"type": "array"},
                        "properties": {"type": "object"}
                    },
                    "required": ["$schema", "title", "type", "properties"]
                }
            },
            "required": ["wizard_id", "schema_content"]
        }
    )
]


# Tool name to function mapping
TOOL_HANDLERS = {
    "federalscout_start_discovery": federalscout_start_discovery,
    "federalscout_click_element": federalscout_click_element,
    "federalscout_execute_actions": federalscout_execute_actions,
    "federalscout_get_page_info": federalscout_get_page_info,
    "federalscout_save_page_metadata": federalscout_save_page_metadata,
    "federalscout_complete_discovery": federalscout_complete_discovery,
    "federalscout_save_schema": federalscout_save_schema
}


@server.list_tools()
async def list_tools() -> list[Tool]:
    """
    List available FederalScout discovery tools.

    Returns:
        List of Tool definitions
    """
    logger.info("Tools list requested")
    return TOOL_DEFINITIONS


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """
    Handle tool calls from MCP client.
    
    Args:
        name: Tool name
        arguments: Tool arguments
        
    Returns:
        List of TextContent with tool results
    """
    logger.info(f"Tool called: {name}")
    logger.debug(f"Tool arguments: {arguments}")
    
    # Get tool handler
    handler = TOOL_HANDLERS.get(name)
    if not handler:
        error_msg = f"Unknown tool: {name}"
        logger.error(error_msg)
        return [TextContent(
            type="text",
            text=f"Error: {error_msg}"
        )]
    
    try:
        # Call tool handler
        result = await handler(**arguments)

        # Check if result contains screenshot - use MCP image content instead of embedding in JSON
        import json
        content_parts = []

        if isinstance(result, dict) and 'screenshot' in result:
            screenshot_b64 = result.pop('screenshot')  # Remove from dict

            # Add screenshot as ImageContent (MDCalc pattern)
            if screenshot_b64:
                content_parts.append(ImageContent(
                    type="image",
                    data=screenshot_b64,
                    mimeType="image/jpeg"
                ))

        # Add text content with remaining data
        result_text = json.dumps(result, indent=2)
        content_parts.append(TextContent(
            type="text",
            text=result_text
        ))

        return content_parts
        
    except Exception as e:
        error_msg = f"Tool execution failed: {str(e)}"
        logger.error(error_msg, exc_info=True)
        
        return [TextContent(
            type="text",
            text=json.dumps({
                "success": False,
                "error": error_msg,
                "error_type": "execution_error"
            }, indent=2)
        )]


async def main():
    """
    Main entry point for FederalScout MCP server.

    Runs the server with stdio transport for Claude Desktop.
    """
    config = get_config()
    logger.info(f"FederalScout MCP Server initialized")
    logger.info(f"Configuration: headless={config.headless}, session_timeout={config.session_timeout}s")
    logger.info(f"Screenshot settings: quality={config.screenshot_quality}, max_size={config.screenshot_max_size_kb}KB")
    logger.info(f"Wizards directory: {config.wizards_dir}")
    
    # Import stdio transport
    from mcp.server.stdio import stdio_server
    
    # Run server with stdio transport
    async with stdio_server() as (read_stream, write_stream):
        logger.info("FederalScout MCP Server running with stdio transport")
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("FederalScout MCP Server shutting down (KeyboardInterrupt)")
    except Exception as e:
        logger.error(f"FederalScout MCP Server error: {e}", exc_info=True)
        sys.exit(1)
