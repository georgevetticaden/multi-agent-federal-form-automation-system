"""
Logging configuration for FederalScout Discovery Agent.

IMPORTANT: Logs to FILE not stdout, since stdio is used for MCP communication.

Reference: requirements/discovery/DISCOVERY_REQUIREMENTS.md
"""

import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional
import json


class StructuredFormatter(logging.Formatter):
    """
    Formatter that outputs structured JSON logs.
    
    This makes logs machine-readable and easier to parse/analyze.
    """
    
    def format(self, record: logging.LogRecord) -> str:
        """
        Format the log record as JSON.
        
        Args:
            record: The log record to format
            
        Returns:
            JSON-formatted log string
        """
        log_data = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
        
        # Add extra fields if present
        if hasattr(record, 'session_id'):
            log_data['session_id'] = record.session_id
        
        if hasattr(record, 'tool_name'):
            log_data['tool_name'] = record.tool_name
        
        if hasattr(record, 'execution_time_ms'):
            log_data['execution_time_ms'] = record.execution_time_ms
        
        return json.dumps(log_data)


class SessionLoggerAdapter(logging.LoggerAdapter):
    """
    Logger adapter that automatically adds session_id to log records.
    """
    
    def process(self, msg, kwargs):
        """Add session_id to the log record."""
        extra = kwargs.get('extra', {})
        extra.update(self.extra)
        kwargs['extra'] = extra
        return msg, kwargs


def setup_logging(
    log_file: Optional[Path] = None,
    level: int = logging.INFO,
    structured: bool = True
) -> logging.Logger:
    """
    Set up logging for FederalScout.

    Args:
        log_file: Path to log file (if None, uses default from config)
        level: Logging level (default: INFO)
        structured: Whether to use structured JSON logging

    Returns:
        Configured logger instance
    """
    # Get or create logger
    logger = logging.getLogger('federalscout')
    logger.setLevel(level)

    # Remove existing handlers
    logger.handlers.clear()

    # Determine log file path
    if log_file is None:
        from config import get_config
        config = get_config()
        log_file = config.get_log_path()

    # Ensure log directory exists
    log_file.parent.mkdir(parents=True, exist_ok=True)

    # Create file handler (NEVER use stdout for FederalScout - conflicts with stdio MCP)
    file_handler = logging.FileHandler(log_file, mode='a')
    file_handler.setLevel(level)
    
    # Set formatter
    if structured:
        formatter = StructuredFormatter()
    else:
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - '
            '%(module)s:%(funcName)s:%(lineno)d - %(message)s'
        )
    
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    # Don't propagate to root logger
    logger.propagate = False
    
    return logger


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """
    Get a logger instance.

    Args:
        name: Logger name (default: 'federalscout')

    Returns:
        Logger instance
    """
    if name is None:
        name = 'federalscout'

    logger = logging.getLogger(name)
    
    # If logger doesn't have handlers, set it up
    if not logger.handlers:
        setup_logging()
    
    return logger


def get_session_logger(session_id: str, logger: Optional[logging.Logger] = None) -> SessionLoggerAdapter:
    """
    Get a logger adapter that automatically includes session_id.

    Args:
        session_id: The session ID to include in logs
        logger: Base logger (default: federalscout logger)

    Returns:
        SessionLoggerAdapter instance
    """
    if logger is None:
        logger = get_logger()

    return SessionLoggerAdapter(logger, {'session_id': session_id})


def log_tool_call(
    tool_name: str,
    params: dict,
    logger: Optional[logging.Logger] = None
):
    """
    Log a tool call with parameters.

    Args:
        tool_name: Name of the tool being called
        params: Parameters passed to the tool
        logger: Logger to use (default: federalscout logger)
    """
    if logger is None:
        logger = get_logger()

    # Don't log sensitive data
    safe_params = {k: v for k, v in params.items() if k not in ['password', 'token', 'secret']}

    # Log with visual separator
    logger.info("━" * 80)
    logger.info(
        f"▶ TOOL CALL: {tool_name}",
        extra={
            'tool_name': tool_name,
            'params': safe_params
        }
    )


def log_tool_result(
    tool_name: str,
    success: bool,
    execution_time_ms: float,
    error: Optional[str] = None,
    logger: Optional[logging.Logger] = None
):
    """
    Log a tool result.

    Args:
        tool_name: Name of the tool that was called
        success: Whether the tool call succeeded
        execution_time_ms: Execution time in milliseconds
        error: Error message if failed
        logger: Logger to use (default: federalscout logger)
    """
    if logger is None:
        logger = get_logger()

    level = logging.INFO if success else logging.ERROR
    status_emoji = "✅" if success else "❌"
    message = f"{status_emoji} RESULT: {tool_name} {'succeeded' if success else 'failed'} ({execution_time_ms:.0f}ms)"

    extra = {
        'tool_name': tool_name,
        'success': success,
        'execution_time_ms': execution_time_ms
    }

    if error:
        extra['error'] = error
        message += f"\n   Error: {error}"

    logger.log(level, message, extra=extra)


def log_session_event(
    session_id: str,
    event: str,
    details: Optional[dict] = None,
    logger: Optional[logging.Logger] = None
):
    """
    Log a session event.

    Args:
        session_id: The session ID
        event: Event type (e.g., 'created', 'closed', 'timeout')
        details: Additional event details
        logger: Logger to use (default: federalscout logger)
    """
    if logger is None:
        logger = get_logger()
    
    extra = {'session_id': session_id, 'event': event}
    if details:
        extra.update(details)
    
    logger.info(f"Session {event}: {session_id}", extra=extra)


# Utility functions for common logging patterns

def log_browser_action(
    action: str,
    selector: Optional[str] = None,
    success: bool = True,
    logger: Optional[logging.Logger] = None
):
    """
    Log a browser action (click, fill, navigate, etc.).
    
    Args:
        action: The action performed
        selector: The selector used (if applicable)
        success: Whether the action succeeded
        logger: Logger to use
    """
    if logger is None:
        logger = get_logger()
    
    message = f"Browser action: {action}"
    if selector:
        message += f" on {selector}"
    
    level = logging.DEBUG if success else logging.WARNING
    logger.log(level, message, extra={'action': action, 'selector': selector, 'success': success})


def log_discovery_progress(
    session_id: str,
    pages_discovered: int,
    current_page: int,
    logger: Optional[logging.Logger] = None
):
    """
    Log discovery progress.
    
    Args:
        session_id: The session ID
        pages_discovered: Total pages discovered so far
        current_page: Current page number
        logger: Logger to use
    """
    if logger is None:
        logger = get_logger()
    
    logger.info(
        f"Discovery progress: page {current_page}, total discovered: {pages_discovered}",
        extra={
            'session_id': session_id,
            'pages_discovered': pages_discovered,
            'current_page': current_page
        }
    )


# Configure logging on module import (with default settings)
_default_logger = setup_logging()
