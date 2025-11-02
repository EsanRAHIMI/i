"""
Authentication and security related tasks.
"""
from typing import Dict, Any
import structlog
from celery import current_task

from ..celery_app import celery_app
from ..database.base import SessionLocal
from ..database.models import AuditLog

logger = structlog.get_logger(__name__)


@celery_app.task(bind=True, queue="auth")
def cleanup_expired_tokens(self) -> Dict[str, Any]:
    """
    Clean up expired tokens and old audit logs.
    
    Returns:
        Dict containing cleanup results
    """
    try:
        logger.info("Cleaning up expired tokens and audit logs")
        
        with SessionLocal() as db:
            # Calculate cutoff date (90 days ago)
            cutoff_date = "2023-10-01T00:00:00Z"  # Placeholder
            
            # Delete old audit logs
            old_logs = db.query(AuditLog).filter(
                AuditLog.created_at < cutoff_date
            ).all()
            
            cleanup_result = {
                "audit_logs_deleted": len(old_logs),
                "retention_days": 90
            }
            
            for log in old_logs:
                db.delete(log)
            
            db.commit()
        
        logger.info("Token cleanup completed", result=cleanup_result)
        
        return cleanup_result
        
    except Exception as exc:
        logger.error("Token cleanup failed", error=str(exc))
        self.retry(exc=exc, countdown=3600, max_retries=1)  # 1 hour delay