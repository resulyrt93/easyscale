"""Logging configuration for EasyScale."""

import logging
import sys
from typing import Optional


def setup_logging(level: str = "INFO", format_json: bool = False) -> None:
    """
    Setup logging configuration.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        format_json: If True, use JSON format (for structured logging)
    """
    log_level = getattr(logging, level.upper(), logging.INFO)

    if format_json:
        # JSON format for structured logging
        log_format = '{"time":"%(asctime)s","level":"%(levelname)s","name":"%(name)s","message":"%(message)s"}'
    else:
        # Human-readable format
        log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    logging.basicConfig(
        level=log_level,
        format=log_format,
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    # Set kubernetes client logging to WARNING to reduce noise
    logging.getLogger("kubernetes").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)


def get_logger(name: str, level: Optional[str] = None) -> logging.Logger:
    """
    Get a logger instance.

    Args:
        name: Logger name (usually __name__)
        level: Optional logging level override

    Returns:
        Logger instance
    """
    logger = logging.getLogger(name)
    if level:
        logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    return logger
