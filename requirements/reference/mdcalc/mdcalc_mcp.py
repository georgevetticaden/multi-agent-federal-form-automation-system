#!/usr/bin/env python3
"""
MDCalc MCP Server - Screenshot-Based Universal Calculator Support

This MCP server provides Claude with access to all 825 MDCalc medical calculators
through visual understanding and browser automation.

Architecture:
    - Screenshot-based: Claude SEES calculators visually (no hardcoded selectors)
    - Universal support: Works with ALL 825 calculators automatically
    - Smart Agent, Dumb Tools: Claude handles intelligence, tools are mechanical
    - Catalog-driven: Complete calculator catalog with categories and metadata

Tools Provided:
    1. mdcalc_list_all: Get catalog of all 825 calculators
    2. mdcalc_search: Search calculators by condition/symptom/name
    3. mdcalc_get_calculator: Get screenshot for visual understanding
    4. mdcalc_execute: Execute calculator with mapped values

Usage:
    Configure in claude_desktop_config.json and Claude will have access
    to all MDCalc calculators for clinical decision support.
"""

import asyncio
import json
import sys
import logging
import re
from typing import Dict, List, Any, Optional
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from mdcalc_client import MDCalcClient

# Configure logging
logging.basicConfig(
    level=logging.WARNING,  # Only show warnings and errors to stderr
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MDCalcMCPServer:
    """
    MCP server for MDCalc automation.
    Provides atomic tools - Claude handles ALL orchestration and intelligence.
    """

    def __init__(self):
        self.client = None
        self.initialized = False

    async def initialize(self):
        """Initialize the MDCalc client."""
        if not self.initialized:
            import os
            self.client = MDCalcClient()
            # Check environment variable for headless mode
            headless = os.environ.get('MDCALC_HEADLESS', 'true').lower() == 'true'
            await self.client.initialize(headless=headless)
            self.initialized = True
            logger.info(f"MDCalc MCP Server initialized (headless={headless})")

    async def handle_request(self, request: Dict) -> Dict:
        """Handle incoming JSON-RPC requests."""
        request_id = request.get('id')
        method = request.get('method')
        params = request.get('params', {})

        try:
            # Initialize client on first tool use
            if method == 'tools/call' and not self.initialized:
                await self.initialize()

            # Handle different methods
            if method == 'initialize':
                return {
                    'jsonrpc': '2.0',
                    'id': request_id,
                    'result': {
                        'protocolVersion': '2024-11-05',
                        'capabilities': {
                            'tools': {}
                        },
                        'serverInfo': {
                            'name': 'mdcalc-automation',
                            'version': '1.0.0'
                        }
                    }
                }

            elif method == 'notifications/initialized':
                # This is a notification, no response needed
                return None

            elif method == 'prompts/list':
                # We don't have prompts, return empty list
                return {
                    'jsonrpc': '2.0',
                    'id': request_id,
                    'result': {
                        'prompts': []
                    }
                }

            elif method == 'resources/list':
                # We don't have resources, return empty list
                return {
                    'jsonrpc': '2.0',
                    'id': request_id,
                    'result': {
                        'resources': []
                    }
                }

            elif method == 'tools/list':
                return {
                    'jsonrpc': '2.0',
                    'id': request_id,
                    'result': {
                        'tools': self.get_tools()
                    }
                }

            elif method == 'tools/call':
                tool_name = params.get('name')
                arguments = params.get('arguments', {})

                result = await self.execute_tool(tool_name, arguments)

                return {
                    'jsonrpc': '2.0',
                    'id': request_id,
                    'result': result
                }

            else:
                # Method not found
                return {
                    'jsonrpc': '2.0',
                    'id': request_id,
                    'error': {
                        'code': -32601,
                        'message': f'Method not found: {method}'
                    }
                }

        except Exception as e:
            logger.error(f"Error handling request: {e}")
            return {
                'jsonrpc': '2.0',
                'id': request_id,
                'error': {
                    'code': -32603,
                    'message': str(e)
                }
            }

    def get_tools(self) -> List[Dict]:
        """
        Return available MDCalc MCP tools.

        These are atomic, mechanical operations. Claude handles ALL intelligence,
        clinical interpretation, and data mapping. The tools simply navigate,
        screenshot, click, and extract.
        """
        return [
            {
                'name': 'mdcalc_list_all',
                'description': (
                    'Get the complete catalog of all 825 MDCalc calculators in an optimized format (~31K tokens). '
                    'Returns compact list with just ID, name, and medical category for each calculator. '
                    'Use for comprehensive assessments where you need to review all available options by specialty. '
                    'URLs can be constructed as: https://www.mdcalc.com/calc/{id}'
                ),
                'inputSchema': {
                    'type': 'object',
                    'properties': {},
                    'required': []
                }
            },
            {
                'name': 'mdcalc_search',
                'description': (
                    'Search MDCalc using their sophisticated web search that understands clinical relationships. '
                    'Returns semantically relevant calculators, not just keyword matches. '
                    'Use for targeted queries when you know what you are looking for. '
                    'Example queries: "chest pain" (finds HEART, TIMI), "afib" (finds CHA2DS2-VASc), "sepsis" (finds SOFA).'
                ),
                'inputSchema': {
                    'type': 'object',
                    'properties': {
                        'query': {
                            'type': 'string',
                            'description': 'Search term - can be condition (e.g., "chest pain"), symptom (e.g., "dyspnea"), body system (e.g., "cardiac"), or calculator name (e.g., "HEART Score")'
                        },
                        'limit': {
                            'type': 'integer',
                            'description': 'Maximum number of results to return (default: 10, max: 50)',
                            'default': 10,
                            'minimum': 1,
                            'maximum': 50
                        }
                    },
                    'required': ['query']
                }
            },
            {
                'name': 'mdcalc_get_calculator',
                'description': (
                    'Get a screenshot and details of a specific MDCalc calculator. '
                    'Returns a JPEG screenshot (23KB) of the calculator interface for visual understanding, '
                    'plus metadata including title and URL. The screenshot shows all input fields, options, '
                    'and current values. YOU must use vision to understand the calculator structure and '
                    'map patient data to the appropriate buttons/inputs shown in the screenshot.'
                ),
                'inputSchema': {
                    'type': 'object',
                    'properties': {
                        'calculator_id': {
                            'type': 'string',
                            'description': (
                                'MDCalc calculator ID or slug. Can be numeric ID (e.g., "1752" for HEART Score) '
                                'or slug format (e.g., "heart-score", "cha2ds2-vasc", "curb-65"). '
                                'Get IDs from mdcalc_search or mdcalc_list_all results.'
                            )
                        }
                    },
                    'required': ['calculator_id']
                }
            },
            {
                'name': 'mdcalc_execute',
                'description': (
                    'Execute a calculator by filling inputs and clicking buttons based on provided values. '
                    'This is a MECHANICAL tool - it only clicks what you tell it. YOU must: '
                    '1) First call mdcalc_get_calculator to SEE the calculator visually, '
                    '2) Map patient data to the EXACT button text or input values shown, '
                    '3) Pass the mapped values to this tool. '
                    'Returns calculation results AND a result screenshot showing all inputs and results. '
                    'ALWAYS examine the result screenshot to verify correct execution and see conditional fields.'
                ),
                'inputSchema': {
                    'type': 'object',
                    'properties': {
                        'calculator_id': {
                            'type': 'string',
                            'description': 'MDCalc calculator ID (e.g., "1752") or slug (e.g., "heart-score")'
                        },
                        'inputs': {
                            'type': 'object',
                            'description': (
                                'Field values mapped to calculator inputs. Keys should be field names '
                                '(e.g., "age", "history", "troponin"). Values must match EXACT button text '
                                'as shown in screenshot (e.g., "≥65", "Moderately suspicious", "≤1x normal limit"). '
                                'For numeric inputs, provide the numeric value. YOU are responsible for all mapping.'
                            ),
                            'additionalProperties': {
                                'type': 'string'
                            }
                        }
                    },
                    'required': ['calculator_id', 'inputs']
                }
            }
        ]

    async def execute_tool(self, tool_name: str, arguments: Dict) -> Dict:
        """
        Execute the specified MDCalc tool with given arguments.

        Returns:
            Dict containing 'content' with tool results:
            - mdcalc_list_all: Optimized catalog (~31K tokens) with ID, name, category
            - mdcalc_search: Web search results with semantic matching
            - mdcalc_get_calculator: Screenshot (JPEG) for visual understanding
            - mdcalc_execute: Calculation results with score and interpretation
        """
        try:
            if tool_name == 'mdcalc_list_all':
                calculators = await self.client.get_all_calculators()

                # Group by category
                by_category = {}
                for calc in calculators:
                    category = calc.get('category', 'Other')
                    if category not in by_category:
                        by_category[category] = []
                    by_category[category].append(calc)

                return {
                    'content': [
                        {
                            'type': 'text',
                            'text': json.dumps({
                                'success': True,
                                'total_count': len(calculators),
                                'categories': list(by_category.keys()),
                                'calculators_by_category': by_category,
                                'all_calculators': calculators
                            }, indent=2)
                        }
                    ]
                }

            elif tool_name == 'mdcalc_search':
                query = arguments.get('query', '')
                limit = arguments.get('limit', 10)

                results = await self.client.search_calculators(query, limit)

                return {
                    'content': [
                        {
                            'type': 'text',
                            'text': json.dumps({
                                'success': True,
                                'count': len(results),
                                'calculators': results
                            }, indent=2)
                        }
                    ]
                }

            elif tool_name == 'mdcalc_get_calculator':
                calculator_id = arguments.get('calculator_id')

                details = await self.client.get_calculator_details(calculator_id)

                # Build response with screenshot as image content
                content = []

                # Add the screenshot as an image if available
                if details.get('screenshot_base64'):
                    content.append({
                        'type': 'image',
                        'data': details['screenshot_base64'],
                        'mimeType': 'image/jpeg'
                    })

                # Add text details (without the base64 data)
                calculator_info = {
                    'success': True,
                    'title': details.get('title'),
                    'url': details.get('url'),
                    'fields_detected': len(details.get('fields', [])),
                    'screenshot_included': bool(details.get('screenshot_base64'))
                }

                content.append({
                    'type': 'text',
                    'text': json.dumps(calculator_info, indent=2)
                })

                return {
                    'content': content
                }

            elif tool_name == 'mdcalc_execute':
                calculator_id = arguments.get('calculator_id')
                inputs = arguments.get('inputs', {})

                result = await self.client.execute_calculator(calculator_id, inputs)

                # Parse the score from the result
                score_text = result.get('score', '')
                risk_text = result.get('risk', '')

                # Extract numeric score if present
                score_value = None
                if score_text and 'point' in score_text.lower():
                    # Extract first number
                    import re
                    match = re.search(r'(\d+)\s*point', score_text.lower())
                    if match:
                        score_value = int(match.group(1))

                # Clean up risk text
                if risk_text:
                    # Extract the actual risk percentage if present
                    risk_match = re.search(r'Risk.*?(\d+\.?\d*%)', risk_text)
                    if risk_match:
                        risk_percentage = risk_match.group(1)
                    else:
                        risk_percentage = None

                    # Extract risk category
                    if 'Low Score' in risk_text:
                        risk_category = 'Low'
                    elif 'Moderate Score' in risk_text:
                        risk_category = 'Moderate'
                    elif 'High Score' in risk_text:
                        risk_category = 'High'
                    else:
                        risk_category = None
                else:
                    risk_percentage = None
                    risk_category = None

                # Build response content
                content = []

                # Include the result screenshot if available
                if result.get('result_screenshot_base64'):
                    content.append({
                        'type': 'image',
                        'data': result['result_screenshot_base64'],
                        'mimeType': 'image/jpeg'
                    })

                # Add text results (without the base64 data)
                text_result = {
                    'success': result.get('success', False),
                    'score': score_value,
                    'score_text': score_text,
                    'risk_category': risk_category,
                    'risk_percentage': risk_percentage,
                    'screenshot_included': bool(result.get('result_screenshot_base64')),
                    'interpretation': result.get('interpretation'),
                    'recommendations': result.get('recommendations')
                }

                # Only include full_result if no screenshot (to avoid duplication)
                if not result.get('result_screenshot_base64'):
                    text_result['full_result'] = {
                        k: v for k, v in result.items()
                        if k != 'result_screenshot_base64'
                    }

                content.append({
                    'type': 'text',
                    'text': json.dumps(text_result, indent=2)
                })

                return {
                    'content': content
                }

            else:
                return {
                    'content': [
                        {
                            'type': 'text',
                            'text': json.dumps({
                                'success': False,
                                'error': f'Unknown tool: {tool_name}'
                            })
                        }
                    ]
                }

        except Exception as e:
            logger.error(f"Error executing tool {tool_name}: {e}")
            return {
                'content': [
                    {
                        'type': 'text',
                        'text': json.dumps({
                            'success': False,
                            'error': str(e)
                        })
                    }
                ]
            }

    async def cleanup(self):
        """Clean up resources."""
        if self.client:
            await self.client.cleanup()
            self.initialized = False


async def main():
    """Main entry point for MCP server."""
    server = MDCalcMCPServer()

    logger.info("MDCalc MCP Server starting...")

    # Read from stdin and write to stdout (MCP protocol)
    while True:
        try:
            # Read line from stdin
            line = await asyncio.get_event_loop().run_in_executor(
                None, sys.stdin.readline
            )

            if not line:
                break

            # Parse JSON-RPC request
            try:
                request = json.loads(line)
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON: {e}")
                continue

            # Handle request
            response = await server.handle_request(request)

            # Send response only if not None (for notifications)
            if response is not None:
                sys.stdout.write(json.dumps(response) + '\n')
                sys.stdout.flush()

        except KeyboardInterrupt:
            break
        except Exception as e:
            logger.error(f"Server error: {e}")
            error_response = {
                'jsonrpc': '2.0',
                'error': {
                    'code': -32603,
                    'message': str(e)
                }
            }
            sys.stdout.write(json.dumps(error_response) + '\n')
            sys.stdout.flush()

    # Cleanup
    await server.cleanup()
    logger.info("MDCalc MCP Server stopped")


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass