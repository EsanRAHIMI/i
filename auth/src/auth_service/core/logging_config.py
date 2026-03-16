"""
Logging configuration for auth service.
"""
import structlog
from contextlib import contextmanager
from typing import Optional


class LoggingContext:
    """Context manager for logging with correlation ID."""
    
    def __init__(self, correlation_id: Optional[str] = None, request_id: Optional[str] = None, user_id: Optional[str] = None):
        self.correlation_id = correlation_id
        self.request_id = request_id
        self.user_id = user_id
        self.bound_logger = None

    def __enter__(self):
        if self.correlation_id or self.request_id or self.user_id:
            context = {}
            if self.correlation_id:
                context["correlation_id"] = self.correlation_id
            if self.request_id:
                context["request_id"] = self.request_id
            if self.user_id:
                context["user_id"] = self.user_id
            
            self.bound_logger = structlog.get_logger().bind(**context)
            return self.bound_logger
        return structlog.get_logger()

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


def configure_logging(
    log_level: str = "INFO",
    service_name: str = "auth-service",
    version: str = "1.0.0",
    enable_json: bool = True,
    log_file: Optional[str] = None
):
    """Configure structured logging."""
    import logging
    import sys
    from structlog.stdlib import LoggerFactory
    from structlog.processors import JSONRenderer, TimeStamper
    from structlog.dev import ConsoleRenderer as DevConsoleRenderer

    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, log_level.upper()),
    )

    # Configure structlog processors
    processors = [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    if enable_json:
        processors.append(JSONRenderer())
    else:
        processors.append(DevConsoleRenderer(colors=True))

    # Configure structlog
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=LoggerFactory(),
        cache_logger_on_first_use=True,
        context_class=dict,
    )

    # Add service context
    logger = structlog.get_logger()
    logger = logger.bind(service=service_name, version=version)
