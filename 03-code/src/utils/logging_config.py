"""
CHUNK-007: Logging Setup

Centralized logging configuration for the Knowledge Extraction System.
Configures console and file logging with appropriate levels.
"""

import logging
import sys


def setup_logging():
    """
    Configure logging for the application.

    Sets up logging with:
    - INFO level for application logs
    - Formatted output with timestamp, logger name, level, and message
    - Console output (stdout)
    - File output (app.log)
    - WARNING level for third-party libraries (SQLAlchemy, PIL)

    Returns:
        logging.Logger: Configured logger instance

    Example:
        >>> from src.utils.logging_config import logger
        >>> logger.info("Application started")
        >>> logger.error("An error occurred")
    """
    # Configure basic logging settings
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('app.log')
        ]
    )

    # Reduce verbosity of third-party library loggers
    logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)
    logging.getLogger('PIL').setLevel(logging.WARNING)

    # Return logger for this module
    return logging.getLogger(__name__)


# Create and configure global logger instance
logger = setup_logging()
