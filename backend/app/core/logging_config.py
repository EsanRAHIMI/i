"""
Comprehensive logging configuration with structured JSON logging and correlation ID tracking.
"""
import sys
import json
import uuid
import time
import logging
import logging.config
from typing import Dict, Any, Optional
from contextvars import ContextVar
from datetime import datetime

import structlog
from structlog.types import Processor
try:
    from pythonjsonlogger.json import JsonFormatter as jsonlogger
except ImportError:
    from pythonjsonlogger import jsonlogger

# Context variables for correlation tracking
correlation_id_var: ContextVar[Optional[str]] = ContextVar('correlation_id', default=None)
user_id_var: ContextVar[Optional[str]] = ContextVar('user_id', default=None)
request_id_var: ContextVar[Optional[str]] = ContextVar('request_id', default=None)


class CorrelationIDProcessor:
    """Processor to add correlation ID to log records."""
    
    def __call__(self, logger, method_name, event_dict):
        correlation_id = correlation_id_var.get()
        user_id = user_id_var.get()
        request_id = request_id_var.get()
        
        if correlation_id:
            event_dict['correlation_id'] = correlation_id
        if user_id:
            event_dict['user_id'] = user_id
        if request_id:
            event_dict['request_id'] = request_id
            
        return event_dict


class TimestampProcessor:
    """Processor to add ISO timestamp to log records."""
    
    def __call__(self, logger, method_name, event_dict):
        event_dict['timestamp'] = datetime.utcnow().isoformat() + 'Z'
        return event_dict


class ServiceInfoProcessor:
    """Processor to add service information to log records."""
    
    def __init__(self, service_name: str = "ai-assistant-backend", version: str = "1.0.0"):
        self.service_name = service_name
        self.version = version
    
    def __call__(self, logger, method_name, event_dict):
        event_dict['service'] = self.service_name
        event_dict['version'] = self.version
        event_dict['level'] = method_name.upper()
        return event_dict


class SecuritySanitizer:
    """Processor to sanitize sensitive information from logs."""
    
    SENSITIVE_KEYS = {
        'password', 'token', 'secret', 'key', 'authorization', 
        'auth', 'credential', 'private', 'jwt', 'oauth'
    }
    
    def __call__(self, logger, method_name, event_dict):
        return self._sanitize_dict(event_dict)
    
    def _sanitize_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively sanitize sensitive data."""
        if not isinstance(data, dict):
            return data
            
        sanitized = {}
        for key, value in data.items():
            if any(sensitive in key.lower() for sensitive in self.SENSITIVE_KEYS):
                sanitized[key] = "[REDACTED]"
            elif isinstance(value, dict):
                sanitized[key] = self._sanitize_dict(value)
            elif isinstance(value, list):
                sanitized[key] = [
                    self._sanitize_dict(item) if isinstance(item, dict) else item
                    for item in value
                ]
            else:
                sanitized[key] = value
        return sanitized


class PerformanceProcessor:
    """Processor to add performance metrics to log records."""
    
    def __call__(self, logger, method_name, event_dict):
        # Add process time if available
        if 'start_time' in event_dict:
            duration = time.time() - event_dict['start_time']
            event_dict['duration_ms'] = round(duration * 1000, 2)
            del event_dict['start_time']  # Remove start_time from final log
        
        return event_dict


def configure_logging(
    log_level: str = "INFO",
    service_name: str = "ai-assistant-backend",
    version: str = "1.0.0",
    enable_json: bool = True,
    log_file: Optional[str] = None
) -> None:
    """Configure structured logging for the application."""
    
    # Configure structlog processors
    processors = [
        structlog.contextvars.merge_contextvars,
        CorrelationIDProcessor(),
        TimestampProcessor(),
        ServiceInfoProcessor(service_name, version),
        SecuritySanitizer(),
        PerformanceProcessor(),
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
    ]
    
    if enable_json:
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.extend([
            structlog.dev.ConsoleRenderer(colors=True),
        ])
    
    # Configure structlog
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, log_level.upper())
        ),
        logger_factory=structlog.WriteLoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    # Configure standard library logging
    logging_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "json": {
                "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
                "format": "%(asctime)s %(name)s %(levelname)s %(message)s %(correlation_id)s %(user_id)s"
            },
            "standard": {
                "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": log_level,
                "formatter": "json" if enable_json else "standard",
                "stream": sys.stdout
            }
        },
        "loggers": {
            "": {  # Root logger
                "handlers": ["console"],
                "level": log_level,
                "propagate": False
            },
            "uvicorn": {
                "handlers": ["console"],
                "level": "INFO",
                "propagate": False
            },
            "uvicorn.access": {
                "handlers": ["console"],
                "level": "INFO",
                "propagate": False
            },
            "sqlalchemy.engine": {
                "handlers": ["console"],
                "level": "WARNING",
                "propagate": False
            },
            "celery": {
                "handlers": ["console"],
                "level": "INFO",
                "propagate": False
            }
        }
    }
    
    # Add file handler if specified
    if log_file:
        import os
        # Create log directory if it doesn't exist
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)
        
        logging_config["handlers"]["file"] = {
            "class": "logging.handlers.RotatingFileHandler",
            "level": log_level,
            "formatter": "json",
            "filename": log_file,
            "maxBytes": 100 * 1024 * 1024,  # 100MB
            "backupCount": 5
        }
        
        # Add file handler to all loggers
        for logger_config in logging_config["loggers"].values():
            logger_config["handlers"].append("file")
    
    logging.config.dictConfig(logging_config)


class LoggingContext:
    """Context manager for adding correlation IDs and other context to logs."""
    
    def __init__(self, correlation_id: Optional[str] = None, 
                 user_id: Optional[str] = None, 
                 request_id: Optional[str] = None,
                 **kwargs):
        self.correlation_id = correlation_id or str(uuid.uuid4())
        self.user_id = user_id
        self.request_id = request_id or str(uuid.uuid4())
        self.extra_context = kwargs
        self.tokens = []
    
    def __enter__(self):
        self.tokens.append(correlation_id_var.set(self.correlation_id))
        if self.user_id:
            self.tokens.append(user_id_var.set(self.user_id))
        if self.request_id:
            self.tokens.append(request_id_var.set(self.request_id))
        
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        for token in reversed(self.tokens):
            token.var.reset(token)


class AuditLogger:
    """Specialized logger for audit events."""
    
    def __init__(self):
        self.logger = structlog.get_logger("audit")
    
    def log_user_action(self, user_id: str, action: str, resource_type: str, 
                       resource_id: Optional[str] = None, 
                       details: Optional[Dict[str, Any]] = None,
                       ip_address: Optional[str] = None,
                       user_agent: Optional[str] = None):
        """Log user actions for audit purposes."""
        self.logger.info(
            "User action performed",
            audit_type="user_action",
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details or {},
            ip_address=ip_address,
            user_agent=user_agent
        )
    
    def log_system_event(self, event_type: str, severity: str, 
                        details: Optional[Dict[str, Any]] = None):
        """Log system events for audit purposes."""
        self.logger.info(
            "System event occurred",
            audit_type="system_event",
            event_type=event_type,
            severity=severity,
            details=details or {}
        )
    
    def log_security_event(self, event_type: str, severity: str, 
                          user_id: Optional[str] = None,
                          ip_address: Optional[str] = None,
                          details: Optional[Dict[str, Any]] = None):
        """Log security events for audit purposes."""
        self.logger.warning(
            "Security event detected",
            audit_type="security_event",
            event_type=event_type,
            severity=severity,
            user_id=user_id,
            ip_address=ip_address,
            details=details or {}
        )
    
    def log_privacy_event(self, event_type: str, user_id: str, 
                         data_type: str, action: str,
                         details: Optional[Dict[str, Any]] = None):
        """Log privacy-related events for compliance."""
        self.logger.info(
            "Privacy event logged",
            audit_type="privacy_event",
            event_type=event_type,
            user_id=user_id,
            data_type=data_type,
            action=action,
            details=details or {}
        )


class PerformanceLogger:
    """Logger for performance metrics and timing."""
    
    def __init__(self):
        self.logger = structlog.get_logger("performance")
    
    def log_operation_timing(self, operation: str, duration_ms: float, 
                           success: bool = True, 
                           details: Optional[Dict[str, Any]] = None):
        """Log operation timing for performance analysis."""
        self.logger.info(
            "Operation completed",
            operation=operation,
            duration_ms=duration_ms,
            success=success,
            details=details or {}
        )
    
    def log_database_query(self, query_type: str, table: str, 
                          duration_ms: float, rows_affected: int = 0):
        """Log database query performance."""
        self.logger.debug(
            "Database query executed",
            query_type=query_type,
            table=table,
            duration_ms=duration_ms,
            rows_affected=rows_affected
        )
    
    def log_external_api_call(self, service: str, endpoint: str, 
                             duration_ms: float, status_code: int,
                             request_size: int = 0, response_size: int = 0):
        """Log external API call performance."""
        self.logger.info(
            "External API call completed",
            service=service,
            endpoint=endpoint,
            duration_ms=duration_ms,
            status_code=status_code,
            request_size=request_size,
            response_size=response_size
        )


# Global logger instances
audit_logger = AuditLogger()
performance_logger = PerformanceLogger()


def get_correlation_id() -> Optional[str]:
    """Get the current correlation ID from context."""
    return correlation_id_var.get()


def set_correlation_id(correlation_id: str) -> None:
    """Set the correlation ID in context."""
    correlation_id_var.set(correlation_id)


def get_user_id() -> Optional[str]:
    """Get the current user ID from context."""
    return user_id_var.get()


def set_user_id(user_id: str) -> None:
    """Set the user ID in context."""
    user_id_var.set(user_id)


# Initialize logging configuration
configure_logging()