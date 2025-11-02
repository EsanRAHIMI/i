"""
Distributed tracing implementation using OpenTelemetry for request flow analysis.
"""
import time
import uuid
import warnings
from typing import Dict, Any, Optional, Callable
from functools import wraps
from contextvars import ContextVar

# Suppress pkg_resources deprecation warning from OpenTelemetry
warnings.filterwarnings("ignore", message=".*pkg_resources.*", category=UserWarning)

import structlog
from opentelemetry import trace
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.semconv.resource import ResourceAttributes

logger = structlog.get_logger(__name__)

# Context variables for tracing
trace_id_var: ContextVar[Optional[str]] = ContextVar('trace_id', default=None)
span_id_var: ContextVar[Optional[str]] = ContextVar('span_id', default=None)


class TracingConfig:
    """Configuration for distributed tracing."""
    
    def __init__(self, 
                 service_name: str = "ai-assistant-backend",
                 service_version: str = "1.0.0",
                 jaeger_endpoint: str = "http://jaeger:14268/api/traces",
                 enable_tracing: bool = True):
        self.service_name = service_name
        self.service_version = service_version
        self.jaeger_endpoint = jaeger_endpoint
        self.enable_tracing = enable_tracing


def configure_tracing(config: TracingConfig) -> None:
    """Configure OpenTelemetry tracing."""
    if not config.enable_tracing:
        logger.info("Tracing is disabled")
        return
    
    # Create resource with service information
    resource = Resource.create({
        ResourceAttributes.SERVICE_NAME: config.service_name,
        ResourceAttributes.SERVICE_VERSION: config.service_version,
        ResourceAttributes.SERVICE_INSTANCE_ID: str(uuid.uuid4()),
    })
    
    # Configure tracer provider
    tracer_provider = TracerProvider(resource=resource)
    trace.set_tracer_provider(tracer_provider)
    
    # Configure Jaeger exporter
    jaeger_exporter = JaegerExporter(
        collector_endpoint=config.jaeger_endpoint,
    )
    
    # Add span processor
    span_processor = BatchSpanProcessor(jaeger_exporter)
    tracer_provider.add_span_processor(span_processor)
    
    # Instrument libraries
    FastAPIInstrumentor().instrument()
    SQLAlchemyInstrumentor().instrument()
    RedisInstrumentor().instrument()
    HTTPXClientInstrumentor().instrument()
    
    logger.info("Distributed tracing configured", 
                service_name=config.service_name,
                jaeger_endpoint=config.jaeger_endpoint)


class CustomTracer:
    """Custom tracer with enhanced functionality."""
    
    def __init__(self, name: str = "ai-assistant"):
        self.tracer = trace.get_tracer(name)
    
    def start_span(self, name: str, attributes: Optional[Dict[str, Any]] = None) -> trace.Span:
        """Start a new span with optional attributes."""
        span = self.tracer.start_span(name)
        
        if attributes:
            for key, value in attributes.items():
                span.set_attribute(key, value)
        
        # Store trace and span IDs in context
        trace_id = format(span.get_span_context().trace_id, '032x')
        span_id = format(span.get_span_context().span_id, '016x')
        
        trace_id_var.set(trace_id)
        span_id_var.set(span_id)
        
        return span
    
    def trace_function(self, operation_name: Optional[str] = None, 
                      attributes: Optional[Dict[str, Any]] = None):
        """Decorator to trace function execution."""
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs):
                span_name = operation_name or f"{func.__module__}.{func.__name__}"
                
                with self.tracer.start_as_current_span(span_name) as span:
                    # Add function attributes
                    span.set_attribute("function.name", func.__name__)
                    span.set_attribute("function.module", func.__module__)
                    
                    # Add custom attributes
                    if attributes:
                        for key, value in attributes.items():
                            span.set_attribute(key, value)
                    
                    # Add argument information (be careful with sensitive data)
                    if args:
                        span.set_attribute("function.args_count", len(args))
                    if kwargs:
                        span.set_attribute("function.kwargs_count", len(kwargs))
                    
                    start_time = time.time()
                    
                    try:
                        result = func(*args, **kwargs)
                        span.set_attribute("function.success", True)
                        return result
                    except Exception as e:
                        span.set_attribute("function.success", False)
                        span.set_attribute("function.error", str(e))
                        span.record_exception(e)
                        raise
                    finally:
                        duration = time.time() - start_time
                        span.set_attribute("function.duration_ms", round(duration * 1000, 2))
            
            return wrapper
        return decorator
    
    def trace_async_function(self, operation_name: Optional[str] = None,
                           attributes: Optional[Dict[str, Any]] = None):
        """Decorator to trace async function execution."""
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            async def wrapper(*args, **kwargs):
                span_name = operation_name or f"{func.__module__}.{func.__name__}"
                
                with self.tracer.start_as_current_span(span_name) as span:
                    # Add function attributes
                    span.set_attribute("function.name", func.__name__)
                    span.set_attribute("function.module", func.__module__)
                    span.set_attribute("function.async", True)
                    
                    # Add custom attributes
                    if attributes:
                        for key, value in attributes.items():
                            span.set_attribute(key, value)
                    
                    start_time = time.time()
                    
                    try:
                        result = await func(*args, **kwargs)
                        span.set_attribute("function.success", True)
                        return result
                    except Exception as e:
                        span.set_attribute("function.success", False)
                        span.set_attribute("function.error", str(e))
                        span.record_exception(e)
                        raise
                    finally:
                        duration = time.time() - start_time
                        span.set_attribute("function.duration_ms", round(duration * 1000, 2))
            
            return wrapper
        return decorator


class AIOperationTracer:
    """Specialized tracer for AI operations."""
    
    def __init__(self):
        self.tracer = CustomTracer("ai-operations")
    
    def trace_voice_processing(self, operation: str):
        """Trace voice processing operations."""
        return self.tracer.trace_async_function(
            operation_name=f"voice.{operation}",
            attributes={
                "ai.operation_type": "voice_processing",
                "ai.operation": operation
            }
        )
    
    def trace_model_inference(self, model_type: str):
        """Trace AI model inference."""
        return self.tracer.trace_async_function(
            operation_name=f"ai.inference.{model_type}",
            attributes={
                "ai.operation_type": "model_inference",
                "ai.model_type": model_type
            }
        )
    
    def trace_intent_recognition(self):
        """Trace intent recognition operations."""
        return self.tracer.trace_async_function(
            operation_name="ai.intent_recognition",
            attributes={
                "ai.operation_type": "intent_recognition"
            }
        )
    
    def trace_task_planning(self):
        """Trace task planning operations."""
        return self.tracer.trace_async_function(
            operation_name="ai.task_planning",
            attributes={
                "ai.operation_type": "task_planning"
            }
        )
    
    def trace_federated_learning(self, operation: str):
        """Trace federated learning operations."""
        return self.tracer.trace_async_function(
            operation_name=f"federated_learning.{operation}",
            attributes={
                "ai.operation_type": "federated_learning",
                "ai.operation": operation
            }
        )


class DatabaseTracer:
    """Specialized tracer for database operations."""
    
    def __init__(self):
        self.tracer = CustomTracer("database")
    
    def trace_query(self, operation: str, table: str):
        """Trace database queries."""
        return self.tracer.trace_async_function(
            operation_name=f"db.{operation}.{table}",
            attributes={
                "db.operation": operation,
                "db.table": table,
                "db.system": "postgresql"
            }
        )
    
    def trace_transaction(self):
        """Trace database transactions."""
        return self.tracer.trace_async_function(
            operation_name="db.transaction",
            attributes={
                "db.operation": "transaction",
                "db.system": "postgresql"
            }
        )


class ExternalAPITracer:
    """Specialized tracer for external API calls."""
    
    def __init__(self):
        self.tracer = CustomTracer("external-api")
    
    def trace_api_call(self, service: str, endpoint: str):
        """Trace external API calls."""
        return self.tracer.trace_async_function(
            operation_name=f"external.{service}.{endpoint}",
            attributes={
                "external.service": service,
                "external.endpoint": endpoint,
                "external.type": "api_call"
            }
        )
    
    def trace_google_calendar(self, operation: str):
        """Trace Google Calendar API calls."""
        return self.tracer.trace_async_function(
            operation_name=f"google_calendar.{operation}",
            attributes={
                "external.service": "google_calendar",
                "external.operation": operation
            }
        )
    
    def trace_whatsapp(self, operation: str):
        """Trace WhatsApp API calls."""
        return self.tracer.trace_async_function(
            operation_name=f"whatsapp.{operation}",
            attributes={
                "external.service": "whatsapp",
                "external.operation": operation
            }
        )


class CacheTracer:
    """Specialized tracer for cache operations."""
    
    def __init__(self):
        self.tracer = CustomTracer("cache")
    
    def trace_cache_operation(self, operation: str):
        """Trace cache operations."""
        return self.tracer.trace_async_function(
            operation_name=f"cache.{operation}",
            attributes={
                "cache.operation": operation,
                "cache.system": "redis"
            }
        )


# Global tracer instances
custom_tracer = CustomTracer()
ai_tracer = AIOperationTracer()
db_tracer = DatabaseTracer()
api_tracer = ExternalAPITracer()
cache_tracer = CacheTracer()


def get_trace_id() -> Optional[str]:
    """Get the current trace ID from context."""
    return trace_id_var.get()


def get_span_id() -> Optional[str]:
    """Get the current span ID from context."""
    return span_id_var.get()


def add_span_attribute(key: str, value: Any) -> None:
    """Add an attribute to the current span."""
    current_span = trace.get_current_span()
    if current_span:
        current_span.set_attribute(key, value)


def record_exception(exception: Exception) -> None:
    """Record an exception in the current span."""
    current_span = trace.get_current_span()
    if current_span:
        current_span.record_exception(exception)


# Initialize tracing (will be called from main.py)
def init_tracing(config: Optional[TracingConfig] = None) -> None:
    """Initialize distributed tracing."""
    if config is None:
        config = TracingConfig()
    
    configure_tracing(config)