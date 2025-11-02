"""
Celery application configuration and setup.
"""
from celery import Celery
from celery.signals import worker_ready, worker_shutting_down
import structlog

from .config import settings

logger = structlog.get_logger(__name__)

# Create Celery instance
celery_app = Celery(
    "intelligent_ai_assistant",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "app.tasks.ai_processing",
        "app.tasks.calendar_sync", 
        "app.tasks.messaging",
        "app.tasks.federated_learning"
    ]
)

# Celery configuration
celery_app.conf.update(
    # Task settings
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    
    # Task routing
    task_routes={
        "app.tasks.ai_processing.*": {"queue": "ai_processing"},
        "app.tasks.calendar_sync.*": {"queue": "calendar_sync"},
        "app.tasks.messaging.*": {"queue": "messaging"},
        "app.tasks.federated_learning.*": {"queue": "federated_learning"},
    },
    
    # Task execution settings
    task_always_eager=False,  # Set to True for testing
    task_eager_propagates=True,
    task_ignore_result=False,
    task_store_eager_result=True,
    
    # Worker settings
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
    worker_disable_rate_limits=False,
    
    # Task retry settings
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_default_retry_delay=60,  # seconds
    task_max_retries=3,
    
    # Result backend settings
    result_expires=3600,  # 1 hour
    result_persistent=True,
    
    # Monitoring
    worker_send_task_events=True,
    task_send_sent_event=True,
    
    # Security
    worker_hijack_root_logger=False,
    worker_log_color=False,
)

# Beat schedule for periodic tasks
celery_app.conf.beat_schedule = {
    "sync_calendars": {
        "task": "app.tasks.calendar_sync.sync_all_calendars",
        "schedule": 300.0,  # Every 5 minutes
    },
    "process_federated_learning": {
        "task": "app.tasks.federated_learning.process_federated_round",
        "schedule": 3600.0,  # Every hour
    },
    "cleanup_expired_tokens": {
        "task": "app.tasks.auth.cleanup_expired_tokens",
        "schedule": 86400.0,  # Daily
    },
}


@worker_ready.connect
def worker_ready_handler(sender=None, **kwargs):
    """Handle worker ready signal."""
    logger.info("Celery worker ready", worker=sender.hostname)


@worker_shutting_down.connect
def worker_shutting_down_handler(sender=None, **kwargs):
    """Handle worker shutdown signal."""
    logger.info("Celery worker shutting down", worker=sender.hostname)


# Task base class with common functionality
class BaseTask(celery_app.Task):
    """Base task class with error handling and logging."""
    
    def on_success(self, retval, task_id, args, kwargs):
        """Called on task success."""
        logger.info(
            "Task completed successfully",
            task_id=task_id,
            task_name=self.name,
            result=retval
        )
    
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Called on task failure."""
        logger.error(
            "Task failed",
            task_id=task_id,
            task_name=self.name,
            error=str(exc),
            traceback=str(einfo)
        )
    
    def on_retry(self, exc, task_id, args, kwargs, einfo):
        """Called on task retry."""
        logger.warning(
            "Task retry",
            task_id=task_id,
            task_name=self.name,
            error=str(exc),
            retry_count=self.request.retries
        )


# Set default task base class
celery_app.Task = BaseTask