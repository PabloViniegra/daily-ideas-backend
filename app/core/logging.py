"""Logging configuration for the application."""

import sys
import structlog
from structlog.typing import FilteringBoundLogger


def setup_logging() -> None:
    """Configure structured logging for the application."""
    
    # Configure structlog
    structlog.configure(
        processors=[
            # Add the log level and a timestamp to the event_dict if the log entry is not from structlog.
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> FilteringBoundLogger:
    """Get a structured logger instance."""
    return structlog.get_logger(name)