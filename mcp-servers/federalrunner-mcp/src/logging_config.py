"""
Logging configuration for FederalRunner Execution Agent.

Cloud Run compatible logging (stdout) with structured formatting.

Reference: requirements/execution/EXECUTION_REQUIREMENTS.md REQ-EXEC-003
"""

import logging
import sys
from datetime import datetime
from typing import Optional


# ANSI color codes for terminal output
class Colors:
    RESET = '\033[0m'
    BOLD = '\033[1m'
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'


class ColoredFormatter(logging.Formatter):
    """Custom formatter with colors for console output."""

    LEVEL_COLORS = {
        logging.DEBUG: Colors.CYAN,
        logging.INFO: Colors.GREEN,
        logging.WARNING: Colors.YELLOW,
        logging.ERROR: Colors.RED,
        logging.CRITICAL: Colors.RED + Colors.BOLD
    }

    def format(self, record):
        """Format log record with colors."""
        # Add color to level name
        if record.levelno in self.LEVEL_COLORS:
            record.levelname = (
                f"{self.LEVEL_COLORS[record.levelno]}"
                f"{record.levelname:8s}"
                f"{Colors.RESET}"
            )
        
        return super().format(record)


def setup_logging(
    level: str = "INFO",
    use_colors: bool = True,
    log_to_file: bool = False,
    log_file: Optional[str] = None
) -> None:
    """
    Set up logging configuration for FederalRunner.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        use_colors: Use colored output for console (default True)
        log_to_file: Also log to file (default False for Cloud Run)
        log_file: Path to log file (if log_to_file is True)
    """
    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper()))

    # Remove existing handlers
    root_logger.handlers.clear()

    # Console handler (stdout for Cloud Run)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)

    # Choose formatter based on color preference
    if use_colors and sys.stdout.isatty():
        console_format = (
            f"{Colors.CYAN}%(asctime)s{Colors.RESET} | "
            f"%(levelname)s | "
            f"{Colors.MAGENTA}%(name)s{Colors.RESET} | "
            f"%(message)s"
        )
        console_formatter = ColoredFormatter(
            console_format,
            datefmt='%H:%M:%S'
        )
    else:
        # Plain format for Cloud Run logs
        console_format = (
            "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
        )
        console_formatter = logging.Formatter(
            console_format,
            datefmt='%Y-%m-%d %H:%M:%S'
        )

    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)

    # File handler (optional, not used in Cloud Run)
    if log_to_file and log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)
        
        file_format = (
            "%(asctime)s | %(levelname)-8s | %(name)s | "
            "%(filename)s:%(lineno)d | %(message)s"
        )
        file_formatter = logging.Formatter(
            file_format,
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for a module.

    Args:
        name: Logger name (usually __name__)

    Returns:
        Logger instance
    """
    return logging.getLogger(name)


def log_execution_action(
    action: str,
    details: str,
    success: bool = True,
    logger: Optional[logging.Logger] = None
) -> None:
    """
    Log an execution action in a structured format.

    Args:
        action: Action type (e.g., 'fill', 'click', 'navigate')
        details: Details about the action
        success: Whether the action succeeded
        logger: Logger instance (uses root if None)
    """
    if logger is None:
        logger = logging.getLogger()

    status = "✓" if success else "✗"
    level = logging.INFO if success else logging.ERROR
    
    message = f"{status} {action:15s} | {details}"
    logger.log(level, message)


# Initialize logging with defaults when module is imported
setup_logging()
