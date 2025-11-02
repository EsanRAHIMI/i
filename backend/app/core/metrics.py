"""
Comprehensive metrics collection for the AI Assistant system.
"""
import time
from typing import Dict, Any, Optional
from prometheus_client import (
    Counter, Histogram, Gauge, Info, 
    CollectorRegistry, generate_latest, CONTENT_TYPE_LATEST
)
import psutil
import structlog

logger = structlog.get_logger(__name__)

# Create custom registry for better organization
REGISTRY = CollectorRegistry()

# HTTP Metrics
HTTP_REQUESTS_TOTAL = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status_code', 'service'],
    registry=REGISTRY
)

HTTP_REQUEST_DURATION = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint', 'service'],
    buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
    registry=REGISTRY
)

HTTP_REQUEST_SIZE = Histogram(
    'http_request_size_bytes',
    'HTTP request size in bytes',
    ['method', 'endpoint'],
    registry=REGISTRY
)

HTTP_RESPONSE_SIZE = Histogram(
    'http_response_size_bytes',
    'HTTP response size in bytes',
    ['method', 'endpoint'],
    registry=REGISTRY
)

# AI/Voice Processing Metrics
VOICE_PROCESSING_DURATION = Histogram(
    'voice_processing_duration_seconds',
    'Voice processing duration in seconds',
    ['operation'],  # 'stt', 'tts', 'intent_recognition'
    buckets=[0.5, 1.0, 2.0, 5.0, 10.0, 30.0],
    registry=REGISTRY
)

VOICE_PROCESSING_TOTAL = Counter(
    'voice_processing_total',
    'Total voice processing operations',
    ['operation', 'status'],  # status: 'success', 'error'
    registry=REGISTRY
)

AI_MODEL_INFERENCE_DURATION = Histogram(
    'ai_model_inference_duration_seconds',
    'AI model inference duration in seconds',
    ['model_type'],  # 'intent_recognition', 'task_planning', 'federated_learning'
    registry=REGISTRY
)

AI_MODEL_ACCURACY = Gauge(
    'ai_model_accuracy_ratio',
    'AI model accuracy ratio',
    ['model_type'],
    registry=REGISTRY
)

# Database Metrics
DATABASE_CONNECTIONS_ACTIVE = Gauge(
    'database_connections_active',
    'Active database connections',
    registry=REGISTRY
)

DATABASE_QUERY_DURATION = Histogram(
    'database_query_duration_seconds',
    'Database query duration in seconds',
    ['operation', 'table'],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5],
    registry=REGISTRY
)

DATABASE_QUERIES_TOTAL = Counter(
    'database_queries_total',
    'Total database queries',
    ['operation', 'table', 'status'],
    registry=REGISTRY
)

# Cache Metrics
CACHE_OPERATIONS_TOTAL = Counter(
    'cache_operations_total',
    'Total cache operations',
    ['operation', 'status'],  # operation: 'get', 'set', 'delete'
    registry=REGISTRY
)

CACHE_HIT_RATIO = Gauge(
    'cache_hit_ratio',
    'Cache hit ratio',
    registry=REGISTRY
)

# Task Queue Metrics
CELERY_TASKS_TOTAL = Counter(
    'celery_tasks_total',
    'Total Celery tasks',
    ['task_name', 'status'],
    registry=REGISTRY
)

CELERY_TASK_DURATION = Histogram(
    'celery_task_duration_seconds',
    'Celery task duration in seconds',
    ['task_name'],
    buckets=[1.0, 5.0, 10.0, 30.0, 60.0, 300.0, 600.0],
    registry=REGISTRY
)

CELERY_QUEUE_SIZE = Gauge(
    'celery_queue_size',
    'Celery queue size',
    ['queue_name'],
    registry=REGISTRY
)

# External API Metrics
EXTERNAL_API_REQUESTS_TOTAL = Counter(
    'external_api_requests_total',
    'Total external API requests',
    ['service', 'endpoint', 'status_code'],
    registry=REGISTRY
)

EXTERNAL_API_DURATION = Histogram(
    'external_api_duration_seconds',
    'External API request duration in seconds',
    ['service', 'endpoint'],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0],
    registry=REGISTRY
)

# System Metrics
SYSTEM_CPU_USAGE = Gauge(
    'system_cpu_usage_percent',
    'System CPU usage percentage',
    registry=REGISTRY
)

SYSTEM_MEMORY_USAGE = Gauge(
    'system_memory_usage_bytes',
    'System memory usage in bytes',
    registry=REGISTRY
)

SYSTEM_DISK_USAGE = Gauge(
    'system_disk_usage_bytes',
    'System disk usage in bytes',
    ['device'],
    registry=REGISTRY
)

# User Activity Metrics
USER_SESSIONS_ACTIVE = Gauge(
    'user_sessions_active',
    'Active user sessions',
    registry=REGISTRY
)

USER_INTERACTIONS_TOTAL = Counter(
    'user_interactions_total',
    'Total user interactions',
    ['interaction_type'],  # 'voice', 'calendar', 'whatsapp', 'task'
    registry=REGISTRY
)

USER_SATISFACTION_SCORE = Gauge(
    'user_satisfaction_score',
    'User satisfaction score',
    ['interaction_type'],
    registry=REGISTRY
)

# Privacy and Security Metrics
PRIVACY_VIOLATIONS_TOTAL = Counter(
    'privacy_violations_total',
    'Total privacy violations detected',
    ['violation_type'],
    registry=REGISTRY
)

SECURITY_EVENTS_TOTAL = Counter(
    'security_events_total',
    'Total security events',
    ['event_type', 'severity'],
    registry=REGISTRY
)

FEDERATED_LEARNING_ROUNDS_TOTAL = Counter(
    'federated_learning_rounds_total',
    'Total federated learning rounds',
    ['status'],
    registry=REGISTRY
)

FEDERATED_LEARNING_PARTICIPANTS = Gauge(
    'federated_learning_participants',
    'Number of federated learning participants',
    registry=REGISTRY
)

# Application Info
APPLICATION_INFO = Info(
    'application_info',
    'Application information',
    registry=REGISTRY
)

# Set application info
APPLICATION_INFO.info({
    'version': '1.0.0',
    'name': 'intelligent-ai-assistant',
    'environment': 'production'
})


class MetricsCollector:
    """Centralized metrics collection and management."""
    
    def __init__(self):
        self.registry = REGISTRY
        self._last_system_update = 0
        self._system_update_interval = 30  # seconds
    
    def record_http_request(self, method: str, endpoint: str, status_code: int, 
                          duration: float, request_size: int = 0, 
                          response_size: int = 0, service: str = "backend"):
        """Record HTTP request metrics."""
        HTTP_REQUESTS_TOTAL.labels(
            method=method,
            endpoint=endpoint,
            status_code=status_code,
            service=service
        ).inc()
        
        HTTP_REQUEST_DURATION.labels(
            method=method,
            endpoint=endpoint,
            service=service
        ).observe(duration)
        
        if request_size > 0:
            HTTP_REQUEST_SIZE.labels(method=method, endpoint=endpoint).observe(request_size)
        
        if response_size > 0:
            HTTP_RESPONSE_SIZE.labels(method=method, endpoint=endpoint).observe(response_size)
    
    def record_voice_processing(self, operation: str, duration: float, success: bool = True):
        """Record voice processing metrics."""
        status = "success" if success else "error"
        
        VOICE_PROCESSING_TOTAL.labels(
            operation=operation,
            status=status
        ).inc()
        
        if success:
            VOICE_PROCESSING_DURATION.labels(operation=operation).observe(duration)
    
    def record_ai_inference(self, model_type: str, duration: float, accuracy: Optional[float] = None):
        """Record AI model inference metrics."""
        AI_MODEL_INFERENCE_DURATION.labels(model_type=model_type).observe(duration)
        
        if accuracy is not None:
            AI_MODEL_ACCURACY.labels(model_type=model_type).set(accuracy)
    
    def record_database_query(self, operation: str, table: str, duration: float, success: bool = True):
        """Record database query metrics."""
        status = "success" if success else "error"
        
        DATABASE_QUERIES_TOTAL.labels(
            operation=operation,
            table=table,
            status=status
        ).inc()
        
        if success:
            DATABASE_QUERY_DURATION.labels(
                operation=operation,
                table=table
            ).observe(duration)
    
    def record_cache_operation(self, operation: str, success: bool = True):
        """Record cache operation metrics."""
        status = "success" if success else "error"
        CACHE_OPERATIONS_TOTAL.labels(operation=operation, status=status).inc()
    
    def record_celery_task(self, task_name: str, duration: float, success: bool = True):
        """Record Celery task metrics."""
        status = "success" if success else "error"
        
        CELERY_TASKS_TOTAL.labels(task_name=task_name, status=status).inc()
        
        if success:
            CELERY_TASK_DURATION.labels(task_name=task_name).observe(duration)
    
    def record_external_api_call(self, service: str, endpoint: str, 
                                duration: float, status_code: int):
        """Record external API call metrics."""
        EXTERNAL_API_REQUESTS_TOTAL.labels(
            service=service,
            endpoint=endpoint,
            status_code=status_code
        ).inc()
        
        EXTERNAL_API_DURATION.labels(
            service=service,
            endpoint=endpoint
        ).observe(duration)
    
    def record_user_interaction(self, interaction_type: str, satisfaction_score: Optional[float] = None):
        """Record user interaction metrics."""
        USER_INTERACTIONS_TOTAL.labels(interaction_type=interaction_type).inc()
        
        if satisfaction_score is not None:
            USER_SATISFACTION_SCORE.labels(interaction_type=interaction_type).set(satisfaction_score)
    
    def record_security_event(self, event_type: str, severity: str):
        """Record security event metrics."""
        SECURITY_EVENTS_TOTAL.labels(event_type=event_type, severity=severity).inc()
    
    def record_privacy_violation(self, violation_type: str):
        """Record privacy violation metrics."""
        PRIVACY_VIOLATIONS_TOTAL.labels(violation_type=violation_type).inc()
    
    def update_system_metrics(self):
        """Update system-level metrics."""
        current_time = time.time()
        
        # Only update system metrics every 30 seconds to avoid overhead
        if current_time - self._last_system_update < self._system_update_interval:
            return
        
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            SYSTEM_CPU_USAGE.set(cpu_percent)
            
            # Memory usage
            memory = psutil.virtual_memory()
            SYSTEM_MEMORY_USAGE.set(memory.used)
            
            # Disk usage
            for disk in psutil.disk_partitions():
                try:
                    usage = psutil.disk_usage(disk.mountpoint)
                    SYSTEM_DISK_USAGE.labels(device=disk.device).set(usage.used)
                except (PermissionError, OSError):
                    # Skip inaccessible disks
                    continue
            
            self._last_system_update = current_time
            
        except Exception as e:
            logger.error("Failed to update system metrics", error=str(e))
    
    def set_active_users(self, count: int):
        """Set the number of active users."""
        USER_SESSIONS_ACTIVE.set(count)
    
    def set_queue_size(self, queue_name: str, size: int):
        """Set queue size metric."""
        CELERY_QUEUE_SIZE.labels(queue_name=queue_name).set(size)
    
    def set_cache_hit_ratio(self, ratio: float):
        """Set cache hit ratio."""
        CACHE_HIT_RATIO.set(ratio)
    
    def set_federated_learning_participants(self, count: int):
        """Set federated learning participants count."""
        FEDERATED_LEARNING_PARTICIPANTS.set(count)
    
    def record_federated_learning_round(self, success: bool = True):
        """Record federated learning round completion."""
        status = "success" if success else "error"
        FEDERATED_LEARNING_ROUNDS_TOTAL.labels(status=status).inc()
    
    def get_metrics(self) -> str:
        """Get all metrics in Prometheus format."""
        self.update_system_metrics()
        return generate_latest(self.registry)


# Global metrics collector instance
metrics_collector = MetricsCollector()