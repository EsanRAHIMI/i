"""
Comprehensive audit logging system with correlation IDs.
Implements security event monitoring and privacy breach detection.
"""
import uuid
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Union
from enum import Enum
import logging
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, func

from ..database.models import AuditLog, User

logger = logging.getLogger(__name__)


class SecurityEventType(Enum):
    """Security event types for monitoring."""
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILURE = "login_failure"
    PASSWORD_CHANGE = "password_change"
    ACCOUNT_LOCKED = "account_locked"
    UNAUTHORIZED_ACCESS = "unauthorized_access"
    DATA_EXPORT = "data_export"
    DATA_DELETION = "data_deletion"
    CONSENT_CHANGE = "consent_change"
    PRIVACY_BREACH = "privacy_breach"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    API_RATE_LIMIT = "api_rate_limit"
    ENCRYPTION_ERROR = "encryption_error"
    KEY_ROTATION = "key_rotation"


class AuditLogger:
    """
    Comprehensive audit logging system for security and compliance.
    Tracks all user actions and system events with correlation IDs.
    """
    
    def __init__(self):
        self.correlation_id = None
        self.security_thresholds = {
            "failed_login_attempts": 5,
            "api_requests_per_minute": 100,
            "data_export_frequency_hours": 24,
            "suspicious_activity_score": 75
        }
    
    def set_correlation_id(self, correlation_id: Optional[str] = None) -> str:
        """
        Set correlation ID for request tracking.
        
        Args:
            correlation_id: Existing correlation ID or None to generate new one
            
        Returns:
            Correlation ID
        """
        if correlation_id is None:
            correlation_id = str(uuid.uuid4())
        
        self.correlation_id = correlation_id
        return correlation_id
    
    def log_action(self,
                  db: Session,
                  user_id: Optional[str],
                  action: str,
                  resource_type: Optional[str] = None,
                  resource_id: Optional[str] = None,
                  details: Optional[Dict[str, Any]] = None,
                  ip_address: Optional[str] = None,
                  user_agent: Optional[str] = None,
                  correlation_id: Optional[str] = None) -> AuditLog:
        """
        Log user or system action for audit trail.
        
        Args:
            db: Database session
            user_id: User ID (None for system actions)
            action: Action performed
            resource_type: Type of resource affected
            resource_id: ID of resource affected
            details: Additional details about the action
            ip_address: User's IP address
            user_agent: User's browser/client information
            correlation_id: Request correlation ID
            
        Returns:
            Created audit log entry
        """
        # Use current correlation ID if not provided
        if correlation_id is None:
            correlation_id = self.correlation_id
        
        # Create audit log entry
        audit_log = AuditLog(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details or {},
            ip_address=ip_address,
            user_agent=user_agent,
            correlation_id=correlation_id,
            created_at=datetime.utcnow()
        )
        
        db.add(audit_log)
        db.commit()
        
        # Check for security events
        self._check_security_events(db, audit_log)
        
        logger.debug(f"Logged action: {action} for user {user_id}")
        return audit_log
    
    def log_security_event(self,
                          db: Session,
                          event_type: SecurityEventType,
                          user_id: Optional[str] = None,
                          details: Optional[Dict[str, Any]] = None,
                          ip_address: Optional[str] = None,
                          user_agent: Optional[str] = None,
                          severity: str = "medium") -> AuditLog:
        """
        Log security-related event with enhanced monitoring.
        
        Args:
            db: Database session
            event_type: Type of security event
            user_id: User ID if applicable
            details: Event details
            ip_address: Source IP address
            user_agent: User agent string
            severity: Event severity (low, medium, high, critical)
            
        Returns:
            Created audit log entry
        """
        enhanced_details = details or {}
        enhanced_details.update({
            "security_event": True,
            "event_type": event_type.value,
            "severity": severity,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        audit_log = self.log_action(
            db=db,
            user_id=user_id,
            action=f"security_event_{event_type.value}",
            resource_type="security",
            details=enhanced_details,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        # Trigger alerts for high/critical severity events
        if severity in ["high", "critical"]:
            self._trigger_security_alert(db, audit_log, event_type, severity)
        
        logger.warning(f"Security event logged: {event_type.value} (severity: {severity})")
        return audit_log
    
    def log_system_action(self,
                         action: str,
                         resource_type: Optional[str] = None,
                         resource_id: Optional[str] = None,
                         details: Optional[Dict[str, Any]] = None) -> None:
        """
        Log system action to file (for actions without database access).
        
        Args:
            action: Action performed
            resource_type: Type of resource affected
            resource_id: ID of resource affected
            details: Additional details
        """
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "action": action,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "details": details or {},
            "correlation_id": self.correlation_id,
            "system_action": True
        }
        
        # Log to structured logger
        logger.info(f"SYSTEM_AUDIT: {json.dumps(log_entry)}")
    
    def get_user_audit_trail(self,
                           db: Session,
                           user_id: str,
                           start_date: Optional[datetime] = None,
                           end_date: Optional[datetime] = None,
                           limit: int = 1000) -> List[Dict[str, Any]]:
        """
        Get audit trail for a specific user.
        
        Args:
            db: Database session
            user_id: User ID
            start_date: Start date for filtering
            end_date: End date for filtering
            limit: Maximum number of records
            
        Returns:
            List of audit log entries
        """
        query = db.query(AuditLog).filter(AuditLog.user_id == user_id)
        
        if start_date:
            query = query.filter(AuditLog.created_at >= start_date)
        
        if end_date:
            query = query.filter(AuditLog.created_at <= end_date)
        
        audit_logs = query.order_by(desc(AuditLog.created_at)).limit(limit).all()
        
        return [
            {
                "id": str(log.id),
                "action": log.action,
                "resource_type": log.resource_type,
                "resource_id": str(log.resource_id) if log.resource_id else None,
                "details": log.details,
                "ip_address": str(log.ip_address) if log.ip_address else None,
                "user_agent": log.user_agent,
                "correlation_id": str(log.correlation_id) if log.correlation_id else None,
                "created_at": log.created_at.isoformat() if log.created_at else None
            }
            for log in audit_logs
        ]
    
    def detect_suspicious_activity(self, db: Session, user_id: str) -> Dict[str, Any]:
        """
        Detect suspicious activity patterns for a user.
        
        Args:
            db: Database session
            user_id: User ID to analyze
            
        Returns:
            Suspicious activity report
        """
        report = {
            "user_id": user_id,
            "analysis_date": datetime.utcnow().isoformat(),
            "risk_score": 0,
            "alerts": [],
            "patterns": {}
        }
        
        # Analyze last 24 hours of activity
        since_date = datetime.utcnow() - timedelta(hours=24)
        
        # Get recent audit logs
        recent_logs = db.query(AuditLog).filter(
            and_(
                AuditLog.user_id == user_id,
                AuditLog.created_at >= since_date
            )
        ).all()
        
        if not recent_logs:
            return report
        
        # Pattern 1: Excessive failed login attempts
        failed_logins = [log for log in recent_logs if log.action == "login_failure"]
        if len(failed_logins) >= self.security_thresholds["failed_login_attempts"]:
            report["alerts"].append({
                "type": "excessive_failed_logins",
                "count": len(failed_logins),
                "threshold": self.security_thresholds["failed_login_attempts"],
                "severity": "high"
            })
            report["risk_score"] += 30
        
        # Pattern 2: Multiple IP addresses
        ip_addresses = set(str(log.ip_address) for log in recent_logs if log.ip_address)
        if len(ip_addresses) > 3:
            report["alerts"].append({
                "type": "multiple_ip_addresses",
                "count": len(ip_addresses),
                "ips": list(ip_addresses),
                "severity": "medium"
            })
            report["risk_score"] += 20
        
        # Pattern 3: Unusual activity hours
        activity_hours = [log.created_at.hour for log in recent_logs]
        unusual_hours = [hour for hour in activity_hours if hour < 6 or hour > 22]
        if len(unusual_hours) > 5:
            report["alerts"].append({
                "type": "unusual_activity_hours",
                "count": len(unusual_hours),
                "severity": "low"
            })
            report["risk_score"] += 10
        
        # Pattern 4: Rapid data export requests
        data_exports = [log for log in recent_logs if log.action == "data_exported"]
        if len(data_exports) > 1:
            report["alerts"].append({
                "type": "multiple_data_exports",
                "count": len(data_exports),
                "severity": "high"
            })
            report["risk_score"] += 40
        
        # Pattern 5: API rate limiting triggers
        rate_limit_events = [log for log in recent_logs if "rate_limit" in log.action]
        if len(rate_limit_events) > 10:
            report["alerts"].append({
                "type": "api_rate_limiting",
                "count": len(rate_limit_events),
                "severity": "medium"
            })
            report["risk_score"] += 15
        
        # Store patterns for analysis
        report["patterns"] = {
            "total_actions": len(recent_logs),
            "unique_ips": len(ip_addresses),
            "failed_logins": len(failed_logins),
            "data_exports": len(data_exports),
            "rate_limit_events": len(rate_limit_events),
            "activity_hours": list(set(activity_hours))
        }
        
        # Log suspicious activity if risk score is high
        if report["risk_score"] >= self.security_thresholds["suspicious_activity_score"]:
            self.log_security_event(
                db=db,
                event_type=SecurityEventType.SUSPICIOUS_ACTIVITY,
                user_id=user_id,
                details={
                    "risk_score": report["risk_score"],
                    "alerts": report["alerts"],
                    "patterns": report["patterns"]
                },
                severity="high"
            )
        
        return report
    
    def _check_security_events(self, db: Session, audit_log: AuditLog) -> None:
        """Check if audit log indicates a security event."""
        # Check for login failures
        if audit_log.action == "login_failure":
            # Count recent failures for this user/IP
            since_time = datetime.utcnow() - timedelta(minutes=15)
            recent_failures = db.query(AuditLog).filter(
                and_(
                    AuditLog.action == "login_failure",
                    AuditLog.ip_address == audit_log.ip_address,
                    AuditLog.created_at >= since_time
                )
            ).count()
            
            if recent_failures >= self.security_thresholds["failed_login_attempts"]:
                self.log_security_event(
                    db=db,
                    event_type=SecurityEventType.LOGIN_FAILURE,
                    user_id=audit_log.user_id,
                    details={
                        "consecutive_failures": recent_failures,
                        "threshold_exceeded": True
                    },
                    ip_address=str(audit_log.ip_address) if audit_log.ip_address else None,
                    severity="high"
                )
        
        # Check for data export frequency
        elif audit_log.action == "data_exported":
            since_time = datetime.utcnow() - timedelta(hours=self.security_thresholds["data_export_frequency_hours"])
            recent_exports = db.query(AuditLog).filter(
                and_(
                    AuditLog.action == "data_exported",
                    AuditLog.user_id == audit_log.user_id,
                    AuditLog.created_at >= since_time
                )
            ).count()
            
            if recent_exports > 1:
                self.log_security_event(
                    db=db,
                    event_type=SecurityEventType.DATA_EXPORT,
                    user_id=audit_log.user_id,
                    details={
                        "exports_in_timeframe": recent_exports,
                        "timeframe_hours": self.security_thresholds["data_export_frequency_hours"]
                    },
                    severity="medium"
                )
    
    def _trigger_security_alert(self,
                              db: Session,
                              audit_log: AuditLog,
                              event_type: SecurityEventType,
                              severity: str) -> None:
        """Trigger security alert for high-severity events."""
        alert_data = {
            "event_type": event_type.value,
            "severity": severity,
            "user_id": audit_log.user_id,
            "timestamp": audit_log.created_at.isoformat() if audit_log.created_at else None,
            "details": audit_log.details,
            "correlation_id": str(audit_log.correlation_id) if audit_log.correlation_id else None
        }
        
        # Log alert to system logger
        logger.critical(f"SECURITY_ALERT: {json.dumps(alert_data)}")
        
        # In a production system, this would also:
        # - Send notifications to security team
        # - Trigger automated response procedures
        # - Update security monitoring dashboards
    
    def generate_security_report(self, db: Session, days: int = 7) -> Dict[str, Any]:
        """
        Generate security monitoring report.
        
        Args:
            db: Database session
            days: Number of days to analyze
            
        Returns:
            Security report
        """
        since_date = datetime.utcnow() - timedelta(days=days)
        
        report = {
            "report_period": {
                "start_date": since_date.isoformat(),
                "end_date": datetime.utcnow().isoformat(),
                "days": days
            },
            "security_events": {},
            "user_activity": {},
            "system_health": {},
            "recommendations": []
        }
        
        # Security events summary
        security_events = db.query(AuditLog).filter(
            and_(
                AuditLog.created_at >= since_date,
                AuditLog.details.contains({"security_event": True})
            )
        ).all()
        
        event_counts = {}
        for event in security_events:
            event_type = event.details.get("event_type", "unknown")
            event_counts[event_type] = event_counts.get(event_type, 0) + 1
        
        report["security_events"] = {
            "total_events": len(security_events),
            "event_types": event_counts,
            "high_severity_events": len([e for e in security_events if e.details.get("severity") == "high"])
        }
        
        # User activity summary
        total_actions = db.query(AuditLog).filter(AuditLog.created_at >= since_date).count()
        unique_users = db.query(AuditLog.user_id).filter(
            and_(
                AuditLog.created_at >= since_date,
                AuditLog.user_id.isnot(None)
            )
        ).distinct().count()
        
        report["user_activity"] = {
            "total_actions": total_actions,
            "unique_active_users": unique_users,
            "average_actions_per_user": total_actions / unique_users if unique_users > 0 else 0
        }
        
        # System health indicators
        failed_actions = db.query(AuditLog).filter(
            and_(
                AuditLog.created_at >= since_date,
                AuditLog.action.contains("failed")
            )
        ).count()
        
        report["system_health"] = {
            "total_failed_actions": failed_actions,
            "failure_rate": (failed_actions / total_actions * 100) if total_actions > 0 else 0,
            "system_status": "healthy" if failed_actions < total_actions * 0.05 else "degraded"
        }
        
        # Generate recommendations
        if report["security_events"]["high_severity_events"] > 0:
            report["recommendations"].append("Review high-severity security events and implement additional controls")
        
        if report["system_health"]["failure_rate"] > 5:
            report["recommendations"].append("Investigate system failures and improve error handling")
        
        if report["user_activity"]["average_actions_per_user"] > 1000:
            report["recommendations"].append("Monitor for potential automated/bot activity")
        
        return report


# Global audit logger instance
_audit_logger: Optional[AuditLogger] = None


def get_audit_logger() -> AuditLogger:
    """Get or create the global audit logger instance."""
    global _audit_logger
    
    if _audit_logger is None:
        _audit_logger = AuditLogger()
    
    return _audit_logger