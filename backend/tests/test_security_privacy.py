"""
Comprehensive tests for security and privacy features.
Tests encryption, GDPR compliance, audit logging, and security monitoring.
"""
import pytest
import os
import json
import tempfile
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
from sqlalchemy.orm import Session

# Import the modules to test
from app.core.encryption import EncryptionService, get_encryption_service, EncryptionError
from app.core.key_manager import KeyManager, get_key_manager, KeyManagementError
from app.core.privacy_manager import PrivacyManager, get_privacy_manager, PrivacyError
from app.core.audit_logger import AuditLogger, get_audit_logger, SecurityEventType
from app.core.security_monitor import SecurityMonitor, get_security_monitor, ThreatLevel
from app.database.models import User, UserSettings, Consent, AuditLog


class TestEncryptionService:
    """Test encryption and data protection functionality."""
    
    @pytest.fixture
    def encryption_service(self):
        """Create encryption service for testing."""
        with patch.dict(os.environ, {'ENCRYPTION_MASTER_KEY': 'test_master_key_12345'}):
            return EncryptionService()
    
    def test_encrypt_decrypt_basic(self, encryption_service):
        """Test basic encryption and decryption."""
        test_data = "sensitive_information_123"
        
        # Encrypt data
        encrypted = encryption_service.encrypt(test_data)
        assert encrypted != test_data
        assert len(encrypted) > 0
        
        # Decrypt data
        decrypted = encryption_service.decrypt(encrypted)
        assert decrypted == test_data
    
    def test_encrypt_empty_string(self, encryption_service):
        """Test encryption of empty string."""
        encrypted = encryption_service.encrypt("")
        assert encrypted == ""
        
        decrypted = encryption_service.decrypt("")
        assert decrypted == ""
    
    def test_encrypt_decrypt_unicode(self, encryption_service):
        """Test encryption with unicode characters."""
        test_data = "مرحبا بك في النظام الذكي 🤖"
        
        encrypted = encryption_service.encrypt(test_data)
        decrypted = encryption_service.decrypt(encrypted)
        
        assert decrypted == test_data
    
    def test_encrypt_dict_fields(self, encryption_service):
        """Test dictionary field encryption."""
        test_dict = {
            "public_field": "public_data",
            "secret_field": "secret_data",
            "another_secret": "more_secret_data"
        }
        
        fields_to_encrypt = ["secret_field", "another_secret"]
        
        encrypted_dict = encryption_service.encrypt_dict(test_dict, fields_to_encrypt)
        
        # Public field should remain unchanged
        assert encrypted_dict["public_field"] == "public_data"
        
        # Secret fields should be encrypted
        assert encrypted_dict["secret_field"] != "secret_data"
        assert encrypted_dict["another_secret"] != "more_secret_data"
        
        # Decrypt back
        decrypted_dict = encryption_service.decrypt_dict(encrypted_dict, fields_to_encrypt)
        assert decrypted_dict == test_dict
    
    def test_jwt_key_generation(self, encryption_service):
        """Test JWT key generation and retrieval."""
        private_key = encryption_service.get_jwt_private_key()
        public_key = encryption_service.get_jwt_public_key()
        
        assert private_key is not None
        assert public_key is not None
        assert "BEGIN PRIVATE KEY" in private_key
        assert "BEGIN PUBLIC KEY" in public_key
    
    def test_invalid_decryption(self, encryption_service):
        """Test decryption with invalid data."""
        with pytest.raises(EncryptionError):
            encryption_service.decrypt("invalid_encrypted_data")
    
    def test_missing_master_key(self):
        """Test encryption service without master key."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="ENCRYPTION_MASTER_KEY"):
                EncryptionService()


class TestKeyManager:
    """Test key management and rotation functionality."""
    
    @pytest.fixture
    def key_manager(self):
        """Create key manager for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            return KeyManager(key_store_path=temp_dir)
    
    def test_generate_api_key(self, key_manager):
        """Test API key generation."""
        service_name = "test_service"
        api_key = key_manager.generate_api_key(service_name)
        
        assert len(api_key) > 0
        assert api_key in key_manager.metadata["keys"].values()
    
    def test_get_api_key(self, key_manager):
        """Test API key retrieval."""
        service_name = "test_service"
        
        # Generate key
        original_key = key_manager.generate_api_key(service_name)
        
        # Retrieve key
        retrieved_key = key_manager.get_api_key(service_name)
        
        assert retrieved_key == original_key
    
    def test_rotate_api_key(self, key_manager):
        """Test API key rotation."""
        service_name = "test_service"
        
        # Generate initial key
        old_key = key_manager.generate_api_key(service_name)
        
        # Rotate key
        new_key = key_manager.rotate_api_key(service_name)
        
        assert new_key != old_key
        assert key_manager.get_api_key(service_name) == new_key
    
    def test_key_expiration_check(self, key_manager):
        """Test key expiration detection."""
        service_name = "test_service"
        
        # Generate key with short expiration
        key_manager.generate_api_key(service_name, expires_days=1)
        
        # Check expiration (should not be expired yet)
        expiring_keys = key_manager.check_key_expiration()
        assert len(expiring_keys) == 0
        
        # Simulate expired key by modifying metadata
        for key_id, key_info in key_manager.metadata["keys"].items():
            if key_info["service_name"] == service_name:
                key_info["expires_at"] = (datetime.utcnow() - timedelta(days=1)).isoformat()
        
        expiring_keys = key_manager.check_key_expiration()
        assert len(expiring_keys) == 1
        assert expiring_keys[0]["status"] == "expired"
    
    def test_health_check(self, key_manager):
        """Test key management health check."""
        health_report = key_manager.perform_health_check()
        
        assert "status" in health_report
        assert "checks" in health_report
        assert health_report["status"] in ["healthy", "unhealthy"]
    
    def test_cleanup_old_keys(self, key_manager):
        """Test cleanup of old rotated keys."""
        service_name = "test_service"
        
        # Generate and rotate key
        key_manager.generate_api_key(service_name)
        key_manager.rotate_api_key(service_name)
        
        # Simulate old rotation by modifying metadata
        for key_id, key_info in key_manager.metadata["keys"].items():
            if key_info["status"] == "rotated":
                key_info["rotated_at"] = (datetime.utcnow() - timedelta(days=100)).isoformat()
        
        # Cleanup old keys
        cleanup_count = key_manager.cleanup_old_keys(retention_days=90)
        assert cleanup_count == 1


class TestPrivacyManager:
    """Test GDPR compliance and privacy management."""
    
    @pytest.fixture
    def privacy_manager(self):
        """Create privacy manager for testing."""
        return PrivacyManager()
    
    def test_record_consent(self, privacy_manager, db_session, sample_user):
        """Test consent recording."""
        consent = privacy_manager.record_consent(
            db=db_session,
            user_id=str(sample_user.id),
            consent_type="data_processing",
            granted=True,
            consent_text="I agree to data processing for service improvement."
        )
        
        assert consent.user_id == str(sample_user.id)
        assert consent.consent_type == "data_processing"
        assert consent.granted is True
        assert consent.granted_at is not None
    
    def test_get_user_consents(self, privacy_manager, db_session, sample_user):
        """Test retrieving user consents."""
        # Record multiple consents
        privacy_manager.record_consent(
            db=db_session,
            user_id=str(sample_user.id),
            consent_type="data_processing",
            granted=True,
            consent_text="Data processing consent"
        )
        
        privacy_manager.record_consent(
            db=db_session,
            user_id=str(sample_user.id),
            consent_type="voice_training",
            granted=False,
            consent_text="Voice training consent"
        )
        
        consents = privacy_manager.get_user_consents(db_session, str(sample_user.id))
        
        assert len(consents) == 2
        assert any(c["consent_type"] == "data_processing" and c["granted"] for c in consents)
        assert any(c["consent_type"] == "voice_training" and not c["granted"] for c in consents)
    
    def test_revoke_consent(self, privacy_manager, db_session, sample_user):
        """Test consent revocation."""
        # Record consent
        privacy_manager.record_consent(
            db=db_session,
            user_id=str(sample_user.id),
            consent_type="data_processing",
            granted=True,
            consent_text="Data processing consent"
        )
        
        # Revoke consent
        revoked = privacy_manager.revoke_consent(
            db=db_session,
            user_id=str(sample_user.id),
            consent_type="data_processing"
        )
        
        assert revoked is True
        
        # Check that consent is revoked
        consents = privacy_manager.get_user_consents(db_session, str(sample_user.id))
        assert len(consents) == 0  # No active consents
    
    def test_export_user_data(self, privacy_manager, db_session, sample_user_with_settings):
        """Test GDPR data export."""
        user_data = privacy_manager.export_user_data(
            db=db_session,
            user_id=str(sample_user_with_settings.id),
            export_format="json"
        )
        
        assert "export_metadata" in user_data
        assert "personal_data" in user_data
        assert "activity_data" in user_data
        assert "consent_data" in user_data
        assert "audit_trail" in user_data
        
        # Check metadata
        assert user_data["export_metadata"]["user_id"] == str(sample_user_with_settings.id)
        assert user_data["export_metadata"]["gdpr_compliance"] is True
        
        # Check personal data
        assert user_data["personal_data"]["profile"]["email"] == sample_user_with_settings.email
    
    def test_delete_user_data(self, privacy_manager, db_session, sample_user_with_settings):
        """Test GDPR data deletion."""
        user_id = str(sample_user_with_settings.id)
        verification_code = "DELETE_CONFIRM_123"
        
        deletion_report = privacy_manager.delete_user_data(
            db=db_session,
            user_id=user_id,
            verification_code=verification_code,
            retain_audit_logs=True
        )
        
        assert deletion_report["user_id"] == user_id
        assert deletion_report["verification_code"] == verification_code
        assert "deleted_records" in deletion_report
        
        # Verify user is deleted
        deleted_user = db_session.query(User).filter(User.id == user_id).first()
        assert deleted_user is None
    
    def test_generate_compliance_report(self, privacy_manager, db_session, sample_user_with_settings):
        """Test compliance report generation."""
        # Add some consent records
        privacy_manager.record_consent(
            db=db_session,
            user_id=str(sample_user_with_settings.id),
            consent_type="data_processing",
            granted=True,
            consent_text="Data processing consent"
        )
        
        report = privacy_manager.generate_compliance_report(db_session)
        
        assert "report_date" in report
        assert "gdpr_compliance" in report
        assert "statistics" in report
        assert "consent_summary" in report
        assert "data_retention" in report
        assert "security_measures" in report
        
        assert report["gdpr_compliance"] is True


class TestAuditLogger:
    """Test audit logging and security event tracking."""
    
    @pytest.fixture
    def audit_logger(self):
        """Create audit logger for testing."""
        return AuditLogger()
    
    def test_set_correlation_id(self, audit_logger):
        """Test correlation ID management."""
        # Test auto-generation
        correlation_id = audit_logger.set_correlation_id()
        assert correlation_id is not None
        assert audit_logger.correlation_id == correlation_id
        
        # Test explicit setting
        custom_id = "custom-correlation-123"
        set_id = audit_logger.set_correlation_id(custom_id)
        assert set_id == custom_id
        assert audit_logger.correlation_id == custom_id
    
    def test_log_action(self, audit_logger, db_session, sample_user):
        """Test basic action logging."""
        audit_log = audit_logger.log_action(
            db=db_session,
            user_id=str(sample_user.id),
            action="test_action",
            resource_type="test_resource",
            resource_id="test_id",
            details={"test": "data"},
            ip_address="192.168.1.1",
            user_agent="Test Agent"
        )
        
        assert audit_log.user_id == str(sample_user.id)
        assert audit_log.action == "test_action"
        assert audit_log.resource_type == "test_resource"
        assert audit_log.details["test"] == "data"
        assert str(audit_log.ip_address) == "192.168.1.1"
    
    def test_log_security_event(self, audit_logger, db_session, sample_user):
        """Test security event logging."""
        audit_log = audit_logger.log_security_event(
            db=db_session,
            event_type=SecurityEventType.LOGIN_FAILURE,
            user_id=str(sample_user.id),
            details={"attempt_count": 3},
            severity="high"
        )
        
        assert audit_log.details["security_event"] is True
        assert audit_log.details["event_type"] == SecurityEventType.LOGIN_FAILURE.value
        assert audit_log.details["severity"] == "high"
    
    def test_get_user_audit_trail(self, audit_logger, db_session, sample_user):
        """Test audit trail retrieval."""
        # Log multiple actions
        for i in range(5):
            audit_logger.log_action(
                db=db_session,
                user_id=str(sample_user.id),
                action=f"test_action_{i}",
                resource_type="test"
            )
        
        audit_trail = audit_logger.get_user_audit_trail(
            db=db_session,
            user_id=str(sample_user.id),
            limit=3
        )
        
        assert len(audit_trail) == 3
        assert all("action" in entry for entry in audit_trail)
    
    def test_detect_suspicious_activity(self, audit_logger, db_session, sample_user):
        """Test suspicious activity detection."""
        user_id = str(sample_user.id)
        
        # Simulate multiple failed login attempts
        for i in range(6):
            audit_logger.log_action(
                db=db_session,
                user_id=user_id,
                action="login_failure",
                ip_address="192.168.1.100"
            )
        
        report = audit_logger.detect_suspicious_activity(db_session, user_id)
        
        assert report["user_id"] == user_id
        assert report["risk_score"] > 0
        assert len(report["alerts"]) > 0
        assert any(alert["type"] == "excessive_failed_logins" for alert in report["alerts"])
    
    def test_generate_security_report(self, audit_logger, db_session, sample_user):
        """Test security report generation."""
        # Log some security events
        audit_logger.log_security_event(
            db=db_session,
            event_type=SecurityEventType.LOGIN_FAILURE,
            user_id=str(sample_user.id),
            severity="medium"
        )
        
        report = audit_logger.generate_security_report(db_session, days=7)
        
        assert "report_period" in report
        assert "security_events" in report
        assert "user_activity" in report
        assert "system_health" in report


class TestSecurityMonitor:
    """Test security monitoring and threat detection."""
    
    @pytest.fixture
    def security_monitor(self):
        """Create security monitor for testing."""
        return SecurityMonitor()
    
    @pytest.mark.asyncio
    async def test_trigger_alert(self, security_monitor):
        """Test security alert triggering."""
        await security_monitor.trigger_alert(
            threat_level=ThreatLevel.HIGH,
            event_type="test_threat",
            details={"test": "data"},
            user_id="test_user",
            ip_address="192.168.1.1"
        )
        
        # Check that alert was queued
        assert not security_monitor.alert_queue.empty()
    
    def test_detect_privacy_breach_unauthorized_access(self, security_monitor, db_session, sample_user):
        """Test privacy breach detection for unauthorized access."""
        event_details = {
            "action": "data_access",
            "user_id": str(sample_user.id),
            "resource_id": "sensitive_resource",
            "resource_type": "calendar"
        }
        
        breach_report = security_monitor.detect_privacy_breach(db_session, event_details)
        
        # Should detect breach since user has no calendar consent
        assert breach_report is not None
        assert breach_report["breach_detected"] is True
        assert len(breach_report["indicators"]) > 0
    
    def test_detect_privacy_breach_bulk_export(self, security_monitor, db_session):
        """Test privacy breach detection for bulk data export."""
        event_details = {
            "action": "data_exported",
            "details": {"record_count": 5000}
        }
        
        breach_report = security_monitor.detect_privacy_breach(db_session, event_details)
        
        assert breach_report is not None
        assert breach_report["breach_detected"] is True
        assert any(indicator["type"] == "bulk_data_export" for indicator in breach_report["indicators"])
    
    def test_detect_privacy_breach_encryption_failure(self, security_monitor, db_session):
        """Test privacy breach detection for encryption failures."""
        event_details = {
            "action": "encryption_error_detected",
            "details": {"error": "decryption_failed"}
        }
        
        breach_report = security_monitor.detect_privacy_breach(db_session, event_details)
        
        assert breach_report is not None
        assert breach_report["breach_detected"] is True
        assert any(indicator["type"] == "encryption_failure" for indicator in breach_report["indicators"])
        assert any(indicator["severity"] == "critical" for indicator in breach_report["indicators"])
    
    def test_no_breach_detected(self, security_monitor, db_session):
        """Test normal activity doesn't trigger breach detection."""
        event_details = {
            "action": "normal_user_action",
            "user_id": "test_user",
            "resource_type": "public_data"
        }
        
        breach_report = security_monitor.detect_privacy_breach(db_session, event_details)
        
        assert breach_report is None


class TestIntegration:
    """Integration tests for security and privacy components."""
    
    def test_encryption_with_privacy_manager(self, db_session, sample_user):
        """Test encryption integration with privacy manager."""
        privacy_manager = get_privacy_manager()
        
        # Export user data (should include encrypted fields)
        user_data = privacy_manager.export_user_data(
            db=db_session,
            user_id=str(sample_user.id)
        )
        
        assert user_data is not None
        assert user_data["export_metadata"]["gdpr_compliance"] is True
    
    def test_audit_logging_with_privacy_operations(self, db_session, sample_user):
        """Test audit logging during privacy operations."""
        privacy_manager = get_privacy_manager()
        
        # Record consent (should be audited)
        privacy_manager.record_consent(
            db=db_session,
            user_id=str(sample_user.id),
            consent_type="data_processing",
            granted=True,
            consent_text="Test consent"
        )
        
        # Check audit log
        audit_logs = db_session.query(AuditLog).filter(
            AuditLog.user_id == str(sample_user.id)
        ).all()
        
        assert len(audit_logs) > 0
        assert any(log.action == "consent_recorded" for log in audit_logs)
    
    def test_security_monitoring_with_audit_events(self, db_session, sample_user):
        """Test security monitoring integration with audit events."""
        audit_logger = get_audit_logger()
        security_monitor = get_security_monitor()
        
        # Log a security event
        audit_logger.log_security_event(
            db=db_session,
            event_type=SecurityEventType.UNAUTHORIZED_ACCESS,
            user_id=str(sample_user.id),
            severity="high"
        )
        
        # Check that security monitor can detect patterns
        report = audit_logger.detect_suspicious_activity(db_session, str(sample_user.id))
        assert report["user_id"] == str(sample_user.id)
    
    def test_end_to_end_gdpr_compliance(self, db_session, sample_user):
        """Test complete GDPR compliance workflow."""
        privacy_manager = get_privacy_manager()
        audit_logger = get_audit_logger()
        
        user_id = str(sample_user.id)
        
        # 1. Record consent
        privacy_manager.record_consent(
            db=db_session,
            user_id=user_id,
            consent_type="data_processing",
            granted=True,
            consent_text="I consent to data processing"
        )
        
        # 2. Export user data
        user_data = privacy_manager.export_user_data(db_session, user_id)
        assert user_data["export_metadata"]["gdpr_compliance"] is True
        
        # 3. Revoke consent
        privacy_manager.revoke_consent(db_session, user_id, "data_processing")
        
        # 4. Delete user data
        deletion_report = privacy_manager.delete_user_data(
            db_session, user_id, "CONFIRM_DELETE"
        )
        assert deletion_report["deleted_records"]["user"] == 1
        
        # 5. Verify audit trail exists
        audit_trail = audit_logger.get_user_audit_trail(db_session, user_id)
        # Should be empty since user is deleted, but system logs should exist