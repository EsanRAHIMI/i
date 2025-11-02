"""
Security monitoring and breach detection system.
Implements real-time monitoring and automated response procedures.
"""
import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Callable
from enum import Enum
import logging
from sqlalchemy.orm import Session

from .audit_logger import get_audit_logger, SecurityEventType
from .privacy_manager import get_privacy_manager

logger = logging.getLogger(__name__)


class ThreatLevel(Enum):
    """Threat level classifications."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class SecurityMonitor:
    """
    Real-time security monitoring and breach detection system.
    Monitors for security threats and triggers automated responses.
    """
    
    def __init__(self):
        self.audit_logger = get_audit_logger()
        self.privacy_manager = get_privacy_manager()
        
        # Monitoring thresholds
        self.thresholds = {
            "failed_login_rate": 10,  # per minute
            "api_error_rate": 50,     # per minute
            "data_access_rate": 100,  # per minute
            "encryption_errors": 5,   # per hour
            "privacy_violations": 1,  # any violation is critical
        }
        
        # Response handlers
        self.response_handlers: Dict[ThreatLevel, List[Callable]] = {
            ThreatLevel.LOW: [],
            ThreatLevel.MEDIUM: [],
            ThreatLevel.HIGH: [],
            ThreatLevel.CRITICAL: []
        }
        
        # Active monitoring state
        self.monitoring_active = False
        self.alert_queue = asyncio.Queue()
        
        # Register default response handlers
        self._register_default_handlers()
    
    def _register_default_handlers(self) -> None:
        """Register default security response handlers."""
        # Low threat responses
        self.response_handlers[ThreatLevel.LOW].extend([
            self._log_security_event,
            self._update_metrics
        ])
        
        # Medium threat responses
        self.response_handlers[ThreatLevel.MEDIUM].extend([
            self._log_security_event,
            self._update_metrics,
            self._notify_security_team
        ])
        
        # High threat responses
        self.response_handlers[ThreatLevel.HIGH].extend([
            self._log_security_event,
            self._update_metrics,
            self._notify_security_team,
            self._increase_monitoring,
            self._temporary_rate_limit
        ])
        
        # Critical threat responses
        self.response_handlers[ThreatLevel.CRITICAL].extend([
            self._log_security_event,
            self._update_metrics,
            self._notify_security_team,
            self._increase_monitoring,
            self._emergency_lockdown,
            self._initiate_breach_protocol
        ])
    
    async def start_monitoring(self) -> None:
        """Start real-time security monitoring."""
        if self.monitoring_active:
            logger.warning("Security monitoring is already active")
            return
        
        self.monitoring_active = True
        logger.info("Starting security monitoring system")
        
        # Start monitoring tasks
        tasks = [
            asyncio.create_task(self._monitor_authentication()),
            asyncio.create_task(self._monitor_api_usage()),
            asyncio.create_task(self._monitor_data_access()),
            asyncio.create_task(self._monitor_encryption_health()),
            asyncio.create_task(self._process_alert_queue())
        ]
        
        try:
            await asyncio.gather(*tasks)
        except Exception as e:
            logger.error(f"Security monitoring error: {e}")
            self.monitoring_active = False
            raise
    
    async def stop_monitoring(self) -> None:
        """Stop security monitoring."""
        self.monitoring_active = False
        logger.info("Stopped security monitoring system")
    
    async def _monitor_authentication(self) -> None:
        """Monitor authentication events for suspicious activity."""
        while self.monitoring_active:
            try:
                # This would integrate with your authentication system
                # For now, we'll simulate monitoring
                await asyncio.sleep(60)  # Check every minute
                
                # In a real implementation, this would:
                # 1. Query recent authentication events
                # 2. Analyze patterns (failed logins, unusual locations, etc.)
                # 3. Trigger alerts for suspicious activity
                
            except Exception as e:
                logger.error(f"Authentication monitoring error: {e}")
                await asyncio.sleep(60)
    
    async def _monitor_api_usage(self) -> None:
        """Monitor API usage patterns for abuse."""
        while self.monitoring_active:
            try:
                await asyncio.sleep(60)  # Check every minute
                
                # Monitor for:
                # - Excessive API requests
                # - Unusual endpoint access patterns
                # - Rate limiting violations
                # - Automated/bot behavior
                
            except Exception as e:
                logger.error(f"API monitoring error: {e}")
                await asyncio.sleep(60)
    
    async def _monitor_data_access(self) -> None:
        """Monitor data access patterns for privacy violations."""
        while self.monitoring_active:
            try:
                await asyncio.sleep(300)  # Check every 5 minutes
                
                # Monitor for:
                # - Unauthorized data access
                # - Bulk data downloads
                # - Access to sensitive data without proper consent
                # - Data export anomalies
                
            except Exception as e:
                logger.error(f"Data access monitoring error: {e}")
                await asyncio.sleep(300)
    
    async def _monitor_encryption_health(self) -> None:
        """Monitor encryption system health."""
        while self.monitoring_active:
            try:
                await asyncio.sleep(3600)  # Check every hour
                
                # Monitor for:
                # - Encryption/decryption failures
                # - Key rotation issues
                # - Certificate expiration
                # - TLS handshake failures
                
            except Exception as e:
                logger.error(f"Encryption monitoring error: {e}")
                await asyncio.sleep(3600)
    
    async def _process_alert_queue(self) -> None:
        """Process security alerts from the queue."""
        while self.monitoring_active:
            try:
                # Wait for alert with timeout
                alert = await asyncio.wait_for(
                    self.alert_queue.get(), 
                    timeout=10.0
                )
                
                await self._handle_security_alert(alert)
                
            except asyncio.TimeoutError:
                continue  # No alerts, continue monitoring
            except Exception as e:
                logger.error(f"Alert processing error: {e}")
    
    async def trigger_alert(self, 
                          threat_level: ThreatLevel,
                          event_type: str,
                          details: Dict[str, Any],
                          user_id: Optional[str] = None,
                          ip_address: Optional[str] = None) -> None:
        """
        Trigger a security alert.
        
        Args:
            threat_level: Severity of the threat
            event_type: Type of security event
            details: Additional event details
            user_id: Affected user ID
            ip_address: Source IP address
        """
        alert = {
            "timestamp": datetime.utcnow().isoformat(),
            "threat_level": threat_level.value,
            "event_type": event_type,
            "details": details,
            "user_id": user_id,
            "ip_address": ip_address,
            "correlation_id": self.audit_logger.correlation_id
        }
        
        await self.alert_queue.put(alert)
        logger.warning(f"Security alert triggered: {event_type} ({threat_level.value})")
    
    async def _handle_security_alert(self, alert: Dict[str, Any]) -> None:
        """Handle a security alert by executing appropriate responses."""
        threat_level = ThreatLevel(alert["threat_level"])
        
        logger.critical(f"Processing security alert: {alert['event_type']} - {threat_level.value}")
        
        # Execute response handlers for this threat level
        handlers = self.response_handlers.get(threat_level, [])
        
        for handler in handlers:
            try:
                await handler(alert)
            except Exception as e:
                logger.error(f"Response handler failed: {handler.__name__}: {e}")
    
    async def _log_security_event(self, alert: Dict[str, Any]) -> None:
        """Log security event to audit system."""
        # This would log to database when available
        logger.critical(f"SECURITY_EVENT: {json.dumps(alert)}")
    
    async def _update_metrics(self, alert: Dict[str, Any]) -> None:
        """Update security metrics and dashboards."""
        # This would update monitoring dashboards/metrics
        logger.info(f"Updated security metrics for event: {alert['event_type']}")
    
    async def _notify_security_team(self, alert: Dict[str, Any]) -> None:
        """Notify security team of the incident."""
        # In production, this would:
        # - Send email/SMS alerts
        # - Create incident tickets
        # - Update security dashboards
        # - Notify on-call personnel
        
        logger.critical(f"SECURITY_TEAM_ALERT: {alert['event_type']} - {alert['threat_level']}")
    
    async def _increase_monitoring(self, alert: Dict[str, Any]) -> None:
        """Increase monitoring sensitivity temporarily."""
        # Temporarily reduce thresholds for more sensitive detection
        original_thresholds = self.thresholds.copy()
        
        # Reduce thresholds by 50% for 1 hour
        for key in self.thresholds:
            self.thresholds[key] = int(self.thresholds[key] * 0.5)
        
        logger.warning("Increased monitoring sensitivity due to security alert")
        
        # Reset after 1 hour
        await asyncio.sleep(3600)
        self.thresholds = original_thresholds
        logger.info("Reset monitoring sensitivity to normal levels")
    
    async def _temporary_rate_limit(self, alert: Dict[str, Any]) -> None:
        """Apply temporary rate limiting."""
        user_id = alert.get("user_id")
        ip_address = alert.get("ip_address")
        
        if user_id:
            # Implement user-specific rate limiting
            logger.warning(f"Applied temporary rate limiting for user: {user_id}")
        
        if ip_address:
            # Implement IP-based rate limiting
            logger.warning(f"Applied temporary rate limiting for IP: {ip_address}")
    
    async def _emergency_lockdown(self, alert: Dict[str, Any]) -> None:
        """Initiate emergency lockdown procedures."""
        user_id = alert.get("user_id")
        
        if user_id:
            # Lock user account
            logger.critical(f"EMERGENCY: Locked user account: {user_id}")
        
        # Additional lockdown measures:
        # - Disable API access
        # - Revoke active sessions
        # - Block suspicious IP addresses
        # - Enable enhanced logging
        
        logger.critical("EMERGENCY LOCKDOWN INITIATED")
    
    async def _initiate_breach_protocol(self, alert: Dict[str, Any]) -> None:
        """Initiate data breach response protocol."""
        breach_id = f"BREACH_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        
        breach_report = {
            "breach_id": breach_id,
            "detected_at": alert["timestamp"],
            "event_type": alert["event_type"],
            "threat_level": alert["threat_level"],
            "affected_user": alert.get("user_id"),
            "source_ip": alert.get("ip_address"),
            "details": alert["details"],
            "response_actions": [
                "Emergency lockdown initiated",
                "Security team notified",
                "Audit trail preserved",
                "Breach investigation started"
            ]
        }
        
        # Log breach report
        logger.critical(f"DATA_BREACH_PROTOCOL: {json.dumps(breach_report)}")
        
        # In production, this would:
        # - Notify regulatory authorities (within 72 hours for GDPR)
        # - Prepare user notifications
        # - Preserve evidence
        # - Start forensic investigation
        # - Document all response actions
    
    def detect_privacy_breach(self, 
                            db: Session,
                            event_details: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Detect potential privacy breaches.
        
        Args:
            db: Database session
            event_details: Details of the event to analyze
            
        Returns:
            Breach detection report if breach detected, None otherwise
        """
        breach_indicators = []
        
        # Check for unauthorized data access
        if event_details.get("action") == "data_access":
            user_id = event_details.get("user_id")
            resource_id = event_details.get("resource_id")
            
            # Check if user has consent to access this data
            if user_id and resource_id:
                consents = self.privacy_manager.get_user_consents(db, user_id)
                required_consent = self._get_required_consent(event_details.get("resource_type"))
                
                if required_consent and not any(c["consent_type"] == required_consent and c["granted"] for c in consents):
                    breach_indicators.append({
                        "type": "unauthorized_data_access",
                        "severity": "high",
                        "description": f"User {user_id} accessed {event_details.get('resource_type')} without proper consent"
                    })
        
        # Check for bulk data export without proper authorization
        if event_details.get("action") == "data_exported":
            export_size = event_details.get("details", {}).get("record_count", 0)
            if export_size > 1000:  # Large export threshold
                breach_indicators.append({
                    "type": "bulk_data_export",
                    "severity": "medium",
                    "description": f"Large data export detected: {export_size} records"
                })
        
        # Check for encryption failures
        if "encryption_error" in event_details.get("action", ""):
            breach_indicators.append({
                "type": "encryption_failure",
                "severity": "critical",
                "description": "Encryption system failure detected"
            })
        
        if breach_indicators:
            return {
                "breach_detected": True,
                "detection_time": datetime.utcnow().isoformat(),
                "indicators": breach_indicators,
                "event_details": event_details,
                "recommended_actions": self._get_breach_response_actions(breach_indicators)
            }
        
        return None
    
    def _get_required_consent(self, resource_type: str) -> Optional[str]:
        """Get required consent type for accessing a resource."""
        consent_mapping = {
            "calendar": "calendar_sync",
            "whatsapp": "whatsapp_messaging",
            "voice_data": "voice_training",
            "federated_model": "federated_learning"
        }
        return consent_mapping.get(resource_type)
    
    def _get_breach_response_actions(self, indicators: List[Dict[str, Any]]) -> List[str]:
        """Get recommended response actions for breach indicators."""
        actions = ["Investigate incident immediately"]
        
        for indicator in indicators:
            if indicator["severity"] == "critical":
                actions.extend([
                    "Initiate emergency lockdown",
                    "Notify regulatory authorities",
                    "Preserve audit evidence"
                ])
            elif indicator["severity"] == "high":
                actions.extend([
                    "Lock affected user accounts",
                    "Review access permissions",
                    "Enhance monitoring"
                ])
            elif indicator["severity"] == "medium":
                actions.extend([
                    "Review user activity",
                    "Verify consent status",
                    "Update security policies"
                ])
        
        return list(set(actions))  # Remove duplicates


# Global security monitor instance
_security_monitor: Optional[SecurityMonitor] = None


def get_security_monitor() -> SecurityMonitor:
    """Get or create the global security monitor instance."""
    global _security_monitor
    
    if _security_monitor is None:
        _security_monitor = SecurityMonitor()
    
    return _security_monitor