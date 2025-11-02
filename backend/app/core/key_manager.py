"""
Secure key management and rotation system.
Handles encryption keys, JWT keys, and API keys with automatic rotation.
"""
import os
import json
import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from pathlib import Path
import logging
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
import base64

from .encryption import get_encryption_service, EncryptionError

logger = logging.getLogger(__name__)


class KeyManager:
    """
    Secure key management system with automatic rotation capabilities.
    Manages encryption keys, JWT keys, and API keys.
    """
    
    def __init__(self, key_store_path: str = "keys"):
        self.key_store_path = Path(key_store_path)
        self.key_store_path.mkdir(exist_ok=True)
        
        # Key metadata file
        self.metadata_file = self.key_store_path / "key_metadata.json"
        
        # Key rotation intervals (in days)
        self.rotation_intervals = {
            "jwt_keys": 30,      # JWT keys rotate every 30 days
            "api_keys": 90,      # API keys rotate every 90 days
            "encryption_key": 365,  # Master encryption key rotates yearly
        }
        
        # Load or initialize key metadata
        self.metadata = self._load_metadata()
    
    def _load_metadata(self) -> Dict[str, Any]:
        """Load key metadata from file."""
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                logger.error(f"Failed to load key metadata: {e}")
        
        # Initialize default metadata
        return {
            "keys": {},
            "rotation_history": [],
            "last_health_check": None
        }
    
    def _save_metadata(self) -> None:
        """Save key metadata to file."""
        try:
            with open(self.metadata_file, 'w') as f:
                json.dump(self.metadata, f, indent=2, default=str)
        except IOError as e:
            logger.error(f"Failed to save key metadata: {e}")
            raise KeyManagementError(f"Failed to save key metadata: {e}")
    
    def generate_api_key(self, 
                        service_name: str, 
                        key_length: int = 32,
                        expires_days: Optional[int] = None) -> str:
        """
        Generate a new API key for a service.
        
        Args:
            service_name: Name of the service (e.g., 'whatsapp', 'google_calendar')
            key_length: Length of the generated key
            expires_days: Number of days until expiration (None for no expiration)
            
        Returns:
            Generated API key
        """
        # Generate secure random key
        api_key = secrets.token_urlsafe(key_length)
        
        # Calculate expiration date
        created_at = datetime.utcnow()
        expires_at = None
        if expires_days:
            expires_at = created_at + timedelta(days=expires_days)
        
        # Store key metadata
        key_id = hashlib.sha256(f"{service_name}_{created_at.isoformat()}".encode()).hexdigest()[:16]
        
        self.metadata["keys"][key_id] = {
            "service_name": service_name,
            "key_type": "api_key",
            "created_at": created_at.isoformat(),
            "expires_at": expires_at.isoformat() if expires_at else None,
            "status": "active",
            "key_hash": hashlib.sha256(api_key.encode()).hexdigest()
        }
        
        # Save encrypted key to file
        key_file = self.key_store_path / f"{service_name}_{key_id}.key"
        encryption_service = get_encryption_service()
        encrypted_key = encryption_service.encrypt(api_key)
        
        with open(key_file, 'w') as f:
            f.write(encrypted_key)
        
        # Set restrictive permissions
        os.chmod(key_file, 0o600)
        
        self._save_metadata()
        
        logger.info(f"Generated new API key for service: {service_name}")
        return api_key
    
    def get_api_key(self, service_name: str) -> Optional[str]:
        """
        Retrieve the active API key for a service.
        
        Args:
            service_name: Name of the service
            
        Returns:
            API key if found and valid, None otherwise
        """
        # Find active key for service
        active_key_id = None
        for key_id, key_info in self.metadata["keys"].items():
            if (key_info["service_name"] == service_name and 
                key_info["status"] == "active" and
                key_info["key_type"] == "api_key"):
                
                # Check if key is expired
                if key_info["expires_at"]:
                    expires_at = datetime.fromisoformat(key_info["expires_at"])
                    if datetime.utcnow() > expires_at:
                        logger.warning(f"API key for {service_name} has expired")
                        key_info["status"] = "expired"
                        self._save_metadata()
                        continue
                
                active_key_id = key_id
                break
        
        if not active_key_id:
            logger.warning(f"No active API key found for service: {service_name}")
            return None
        
        # Load and decrypt key
        key_file = self.key_store_path / f"{service_name}_{active_key_id}.key"
        if not key_file.exists():
            logger.error(f"API key file not found: {key_file}")
            return None
        
        try:
            with open(key_file, 'r') as f:
                encrypted_key = f.read()
            
            encryption_service = get_encryption_service()
            api_key = encryption_service.decrypt(encrypted_key)
            
            return api_key
            
        except Exception as e:
            logger.error(f"Failed to decrypt API key for {service_name}: {e}")
            return None
    
    def rotate_api_key(self, service_name: str) -> str:
        """
        Rotate API key for a service.
        
        Args:
            service_name: Name of the service
            
        Returns:
            New API key
        """
        logger.info(f"Starting API key rotation for service: {service_name}")
        
        # Mark current key as rotated
        for key_id, key_info in self.metadata["keys"].items():
            if (key_info["service_name"] == service_name and 
                key_info["status"] == "active" and
                key_info["key_type"] == "api_key"):
                key_info["status"] = "rotated"
                key_info["rotated_at"] = datetime.utcnow().isoformat()
        
        # Generate new key
        new_key = self.generate_api_key(service_name)
        
        # Record rotation in history
        self.metadata["rotation_history"].append({
            "service_name": service_name,
            "key_type": "api_key",
            "rotated_at": datetime.utcnow().isoformat(),
            "reason": "scheduled_rotation"
        })
        
        self._save_metadata()
        
        logger.info(f"API key rotation completed for service: {service_name}")
        return new_key
    
    def rotate_jwt_keys(self) -> None:
        """Rotate JWT signing keys."""
        logger.info("Starting JWT key rotation")
        
        try:
            encryption_service = get_encryption_service()
            encryption_service.rotate_keys()
            
            # Record rotation in history
            self.metadata["rotation_history"].append({
                "service_name": "jwt",
                "key_type": "jwt_keys",
                "rotated_at": datetime.utcnow().isoformat(),
                "reason": "scheduled_rotation"
            })
            
            self._save_metadata()
            
            logger.info("JWT key rotation completed successfully")
            
        except Exception as e:
            logger.error(f"JWT key rotation failed: {e}")
            raise KeyManagementError(f"JWT key rotation failed: {e}")
    
    def check_key_expiration(self) -> List[Dict[str, Any]]:
        """
        Check for keys that are expiring soon or have expired.
        
        Returns:
            List of keys that need attention
        """
        expiring_keys = []
        current_time = datetime.utcnow()
        
        for key_id, key_info in self.metadata["keys"].items():
            if key_info["status"] != "active":
                continue
            
            # Check API key expiration
            if key_info["key_type"] == "api_key" and key_info["expires_at"]:
                expires_at = datetime.fromisoformat(key_info["expires_at"])
                days_until_expiry = (expires_at - current_time).days
                
                if days_until_expiry <= 7:  # Warn 7 days before expiration
                    expiring_keys.append({
                        "key_id": key_id,
                        "service_name": key_info["service_name"],
                        "key_type": key_info["key_type"],
                        "expires_at": key_info["expires_at"],
                        "days_until_expiry": days_until_expiry,
                        "status": "expired" if days_until_expiry < 0 else "expiring"
                    })
            
            # Check rotation schedule
            created_at = datetime.fromisoformat(key_info["created_at"])
            key_age_days = (current_time - created_at).days
            
            rotation_interval = self.rotation_intervals.get(key_info["key_type"], 365)
            
            if key_age_days >= rotation_interval:
                expiring_keys.append({
                    "key_id": key_id,
                    "service_name": key_info["service_name"],
                    "key_type": key_info["key_type"],
                    "created_at": key_info["created_at"],
                    "age_days": key_age_days,
                    "status": "needs_rotation"
                })
        
        return expiring_keys
    
    def perform_health_check(self) -> Dict[str, Any]:
        """
        Perform comprehensive health check on key management system.
        
        Returns:
            Health check results
        """
        health_status = {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "checks": {},
            "warnings": [],
            "errors": []
        }
        
        try:
            # Check key store directory
            if not self.key_store_path.exists():
                health_status["errors"].append("Key store directory does not exist")
                health_status["status"] = "unhealthy"
            
            # Check metadata file
            if not self.metadata_file.exists():
                health_status["warnings"].append("Key metadata file does not exist")
            
            # Check encryption service
            try:
                encryption_service = get_encryption_service()
                test_data = "health_check_test"
                encrypted = encryption_service.encrypt(test_data)
                decrypted = encryption_service.decrypt(encrypted)
                
                if decrypted != test_data:
                    health_status["errors"].append("Encryption service test failed")
                    health_status["status"] = "unhealthy"
                else:
                    health_status["checks"]["encryption_service"] = "ok"
                    
            except Exception as e:
                health_status["errors"].append(f"Encryption service error: {e}")
                health_status["status"] = "unhealthy"
            
            # Check for expiring keys
            expiring_keys = self.check_key_expiration()
            if expiring_keys:
                health_status["warnings"].append(f"Found {len(expiring_keys)} keys needing attention")
                health_status["checks"]["key_expiration"] = expiring_keys
            else:
                health_status["checks"]["key_expiration"] = "ok"
            
            # Check JWT keys
            try:
                encryption_service = get_encryption_service()
                private_key = encryption_service.get_jwt_private_key()
                public_key = encryption_service.get_jwt_public_key()
                
                if private_key and public_key:
                    health_status["checks"]["jwt_keys"] = "ok"
                else:
                    health_status["errors"].append("JWT keys not available")
                    health_status["status"] = "unhealthy"
                    
            except Exception as e:
                health_status["errors"].append(f"JWT key check failed: {e}")
                health_status["status"] = "unhealthy"
            
            # Update last health check timestamp
            self.metadata["last_health_check"] = health_status["timestamp"]
            self._save_metadata()
            
        except Exception as e:
            health_status["errors"].append(f"Health check failed: {e}")
            health_status["status"] = "unhealthy"
        
        return health_status
    
    def cleanup_old_keys(self, retention_days: int = 90) -> int:
        """
        Clean up old rotated keys beyond retention period.
        
        Args:
            retention_days: Number of days to retain old keys
            
        Returns:
            Number of keys cleaned up
        """
        cleanup_count = 0
        cutoff_date = datetime.utcnow() - timedelta(days=retention_days)
        
        keys_to_remove = []
        
        for key_id, key_info in self.metadata["keys"].items():
            if key_info["status"] in ["rotated", "expired"]:
                # Check if key is old enough to clean up
                rotated_at = key_info.get("rotated_at") or key_info.get("expires_at")
                if rotated_at:
                    rotated_date = datetime.fromisoformat(rotated_at)
                    if rotated_date < cutoff_date:
                        keys_to_remove.append(key_id)
        
        # Remove old keys
        for key_id in keys_to_remove:
            key_info = self.metadata["keys"][key_id]
            service_name = key_info["service_name"]
            
            # Remove key file
            key_file = self.key_store_path / f"{service_name}_{key_id}.key"
            if key_file.exists():
                key_file.unlink()
            
            # Remove from metadata
            del self.metadata["keys"][key_id]
            cleanup_count += 1
        
        if cleanup_count > 0:
            self._save_metadata()
            logger.info(f"Cleaned up {cleanup_count} old keys")
        
        return cleanup_count


class KeyManagementError(Exception):
    """Custom exception for key management errors."""
    pass


# Global key manager instance
_key_manager: Optional[KeyManager] = None


def get_key_manager() -> KeyManager:
    """Get or create the global key manager instance."""
    global _key_manager
    
    if _key_manager is None:
        _key_manager = KeyManager()
    
    return _key_manager