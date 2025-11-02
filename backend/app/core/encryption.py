"""
AES-256 encryption service for sensitive data protection.
Implements secure key management and data encryption/decryption.
"""
import os
import base64
import secrets
from typing import Optional, Dict, Any
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.backends import default_backend
import logging

logger = logging.getLogger(__name__)


class EncryptionService:
    """
    AES-256 encryption service for protecting sensitive data at rest.
    Supports both symmetric and asymmetric encryption.
    """
    
    def __init__(self, master_key: Optional[str] = None):
        """Initialize encryption service with master key."""
        self._master_key = master_key or os.getenv("ENCRYPTION_MASTER_KEY")
        if not self._master_key:
            raise ValueError("ENCRYPTION_MASTER_KEY environment variable is required")
        
        # Derive encryption key from master key
        self._fernet = self._create_fernet_key(self._master_key)
        
        # RSA key pair for asymmetric encryption (JWT keys)
        self._private_key = None
        self._public_key = None
        self._load_or_generate_rsa_keys()
    
    def _create_fernet_key(self, master_key: str) -> Fernet:
        """Create Fernet encryption key from master key using PBKDF2."""
        # Use a fixed salt for deterministic key derivation
        # In production, consider using per-field salts for additional security
        salt = b"intelligent_ai_assistant_salt_2024"
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
            backend=default_backend()
        )
        
        key = base64.urlsafe_b64encode(kdf.derive(master_key.encode()))
        return Fernet(key)
    
    def _load_or_generate_rsa_keys(self) -> None:
        """Load existing RSA keys or generate new ones for JWT signing."""
        private_key_path = "keys/jwt_private_key.pem"
        public_key_path = "keys/jwt_public_key.pem"
        
        # Create keys directory if it doesn't exist
        os.makedirs("keys", exist_ok=True)
        
        try:
            # Try to load existing keys
            if os.path.exists(private_key_path) and os.path.exists(public_key_path):
                with open(private_key_path, "rb") as f:
                    self._private_key = serialization.load_pem_private_key(
                        f.read(),
                        password=None,
                        backend=default_backend()
                    )
                
                with open(public_key_path, "rb") as f:
                    self._public_key = serialization.load_pem_public_key(
                        f.read(),
                        backend=default_backend()
                    )
                
                logger.info("Loaded existing RSA key pair for JWT signing")
            else:
                raise FileNotFoundError("RSA keys not found, generating new ones")
                
        except (FileNotFoundError, ValueError) as e:
            logger.info(f"Generating new RSA key pair: {e}")
            self._generate_rsa_keys(private_key_path, public_key_path)
    
    def _generate_rsa_keys(self, private_key_path: str, public_key_path: str) -> None:
        """Generate new RSA key pair for JWT signing."""
        # Generate private key
        self._private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=default_backend()
        )
        
        # Get public key
        self._public_key = self._private_key.public_key()
        
        # Save private key
        private_pem = self._private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        
        with open(private_key_path, "wb") as f:
            f.write(private_pem)
        
        # Save public key
        public_pem = self._public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        
        with open(public_key_path, "wb") as f:
            f.write(public_pem)
        
        # Set restrictive permissions
        os.chmod(private_key_path, 0o600)
        os.chmod(public_key_path, 0o644)
        
        logger.info("Generated new RSA key pair for JWT signing")
    
    def encrypt(self, data: str) -> str:
        """
        Encrypt sensitive data using AES-256.
        
        Args:
            data: Plain text data to encrypt
            
        Returns:
            Base64 encoded encrypted data
        """
        if not data:
            return ""
        
        try:
            encrypted_data = self._fernet.encrypt(data.encode('utf-8'))
            return base64.urlsafe_b64encode(encrypted_data).decode('utf-8')
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            raise EncryptionError(f"Failed to encrypt data: {e}")
    
    def decrypt(self, encrypted_data: str) -> str:
        """
        Decrypt sensitive data using AES-256.
        
        Args:
            encrypted_data: Base64 encoded encrypted data
            
        Returns:
            Decrypted plain text data
        """
        if not encrypted_data:
            return ""
        
        try:
            decoded_data = base64.urlsafe_b64decode(encrypted_data.encode('utf-8'))
            decrypted_data = self._fernet.decrypt(decoded_data)
            return decrypted_data.decode('utf-8')
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise EncryptionError(f"Failed to decrypt data: {e}")
    
    def encrypt_dict(self, data: Dict[str, Any], fields_to_encrypt: list) -> Dict[str, Any]:
        """
        Encrypt specific fields in a dictionary.
        
        Args:
            data: Dictionary containing data
            fields_to_encrypt: List of field names to encrypt
            
        Returns:
            Dictionary with specified fields encrypted
        """
        encrypted_data = data.copy()
        
        for field in fields_to_encrypt:
            if field in encrypted_data and encrypted_data[field]:
                encrypted_data[field] = self.encrypt(str(encrypted_data[field]))
        
        return encrypted_data
    
    def decrypt_dict(self, data: Dict[str, Any], fields_to_decrypt: list) -> Dict[str, Any]:
        """
        Decrypt specific fields in a dictionary.
        
        Args:
            data: Dictionary containing encrypted data
            fields_to_decrypt: List of field names to decrypt
            
        Returns:
            Dictionary with specified fields decrypted
        """
        decrypted_data = data.copy()
        
        for field in fields_to_decrypt:
            if field in decrypted_data and decrypted_data[field]:
                decrypted_data[field] = self.decrypt(decrypted_data[field])
        
        return decrypted_data
    
    def get_jwt_private_key(self) -> str:
        """Get JWT private key in PEM format."""
        if not self._private_key:
            raise EncryptionError("RSA private key not available")
        
        return self._private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        ).decode('utf-8')
    
    def get_jwt_public_key(self) -> str:
        """Get JWT public key in PEM format."""
        if not self._public_key:
            raise EncryptionError("RSA public key not available")
        
        return self._public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ).decode('utf-8')
    
    def rotate_keys(self) -> None:
        """Rotate encryption keys for enhanced security."""
        logger.info("Starting key rotation process")
        
        # Generate new RSA keys
        private_key_path = "keys/jwt_private_key.pem"
        public_key_path = "keys/jwt_public_key.pem"
        
        # Backup old keys
        if os.path.exists(private_key_path):
            backup_private = f"keys/jwt_private_key_backup_{secrets.token_hex(8)}.pem"
            backup_public = f"keys/jwt_public_key_backup_{secrets.token_hex(8)}.pem"
            
            os.rename(private_key_path, backup_private)
            os.rename(public_key_path, backup_public)
            
            logger.info(f"Backed up old keys to {backup_private} and {backup_public}")
        
        # Generate new keys
        self._generate_rsa_keys(private_key_path, public_key_path)
        
        logger.info("Key rotation completed successfully")
    
    def generate_secure_token(self, length: int = 32) -> str:
        """Generate a cryptographically secure random token."""
        return secrets.token_urlsafe(length)


class EncryptionError(Exception):
    """Custom exception for encryption-related errors."""
    pass


# Global encryption service instance
_encryption_service: Optional[EncryptionService] = None


def get_encryption_service() -> EncryptionService:
    """Get or create the global encryption service instance."""
    global _encryption_service
    
    if _encryption_service is None:
        _encryption_service = EncryptionService()
    
    return _encryption_service


def encrypt_sensitive_fields(model_data: Dict[str, Any], model_name: str) -> Dict[str, Any]:
    """
    Encrypt sensitive fields based on model type.
    
    Args:
        model_data: Dictionary containing model data
        model_name: Name of the model (e.g., 'Calendar', 'User')
        
    Returns:
        Dictionary with sensitive fields encrypted
    """
    encryption_service = get_encryption_service()
    
    # Define sensitive fields for each model
    sensitive_fields_map = {
        'Calendar': ['access_token_encrypted', 'refresh_token_encrypted'],
        'User': ['password_hash'],
        'ClientUpdate': ['model_delta_encrypted'],
        'WhatsAppMessage': ['content'],  # Optional: encrypt message content
    }
    
    fields_to_encrypt = sensitive_fields_map.get(model_name, [])
    
    if fields_to_encrypt:
        return encryption_service.encrypt_dict(model_data, fields_to_encrypt)
    
    return model_data


def decrypt_sensitive_fields(model_data: Dict[str, Any], model_name: str) -> Dict[str, Any]:
    """
    Decrypt sensitive fields based on model type.
    
    Args:
        model_data: Dictionary containing encrypted model data
        model_name: Name of the model (e.g., 'Calendar', 'User')
        
    Returns:
        Dictionary with sensitive fields decrypted
    """
    encryption_service = get_encryption_service()
    
    # Define sensitive fields for each model
    sensitive_fields_map = {
        'Calendar': ['access_token_encrypted', 'refresh_token_encrypted'],
        'User': ['password_hash'],
        'ClientUpdate': ['model_delta_encrypted'],
        'WhatsAppMessage': ['content'],  # Optional: decrypt message content
    }
    
    fields_to_decrypt = sensitive_fields_map.get(model_name, [])
    
    if fields_to_decrypt:
        return encryption_service.decrypt_dict(model_data, fields_to_decrypt)
    
    return model_data