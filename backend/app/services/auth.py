"""
Authentication and JWT token services.
"""
import jwt
import uuid
import hashlib
import bcrypt
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple
from passlib.context import CryptContext
from sqlalchemy.orm import Session
import structlog
import os
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend

from ..config import settings
from ..database.models import User, UserSettings, AuditLog
from ..schemas.auth import UserCreate, UserLogin, TokenResponse, UserResponse

logger = structlog.get_logger(__name__)

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Bcrypt maximum password length is 72 bytes
BCRYPT_MAX_PASSWORD_LENGTH = 72


class AuthService:
    """Authentication service for user management and JWT tokens."""
    
    def __init__(self):
        self.algorithm = settings.JWT_ALGORITHM
        self.access_token_expire_minutes = settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES
        self.refresh_token_expire_days = settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS
        
        # Load JWT keys from settings, environment, or generate/load from files
        self.private_key, self.public_key = self._load_jwt_keys()
    
    def _load_jwt_keys(self) -> Tuple[str, str]:
        """
        Load JWT keys from settings, environment variables, or files.
        If not found, generate new keys and save them to files.
        
        Returns:
            Tuple of (private_key, public_key) as PEM-formatted strings
        """
        # First, try to use keys from settings/environment
        if settings.JWT_PRIVATE_KEY and settings.JWT_PUBLIC_KEY:
            try:
                # Validate that keys are in PEM format
                private_key_obj = serialization.load_pem_private_key(
                    settings.JWT_PRIVATE_KEY.encode('utf-8'),
                    password=None,
                    backend=default_backend()
                )
                public_key_obj = serialization.load_pem_public_key(
                    settings.JWT_PUBLIC_KEY.encode('utf-8'),
                    backend=default_backend()
                )
                logger.info("Loaded JWT keys from settings/environment")
                return settings.JWT_PRIVATE_KEY, settings.JWT_PUBLIC_KEY
            except Exception as e:
                logger.warning(f"Failed to load JWT keys from settings: {e}, trying file-based keys")
        
        # Second, try to load from files
        keys_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "keys")
        private_key_path = os.path.join(keys_dir, "jwt_private_key.pem")
        public_key_path = os.path.join(keys_dir, "jwt_public_key.pem")
        
        if os.path.exists(private_key_path) and os.path.exists(public_key_path):
            try:
                with open(private_key_path, "r") as f:
                    private_key_pem = f.read()
                with open(public_key_path, "r") as f:
                    public_key_pem = f.read()
                
                # Validate keys
                serialization.load_pem_private_key(
                    private_key_pem.encode('utf-8'),
                    password=None,
                    backend=default_backend()
                )
                serialization.load_pem_public_key(
                    public_key_pem.encode('utf-8'),
                    backend=default_backend()
                )
                
                logger.info("Loaded JWT keys from files")
                return private_key_pem, public_key_pem
            except Exception as e:
                logger.warning(f"Failed to load JWT keys from files: {e}, generating new keys")
        
        # Finally, generate new keys and save them
        logger.info("Generating new JWT key pair")
        os.makedirs(keys_dir, exist_ok=True)
        
        private_key_obj = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=default_backend()
        )
        public_key_obj = private_key_obj.public_key()
        
        # Serialize keys to PEM format
        private_key_pem = private_key_obj.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        ).decode('utf-8')
        
        public_key_pem = public_key_obj.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ).decode('utf-8')
        
        # Save keys to files
        try:
            with open(private_key_path, "w") as f:
                f.write(private_key_pem)
            with open(public_key_path, "w") as f:
                f.write(public_key_pem)
            logger.info(f"Generated and saved JWT keys to {keys_dir}")
        except Exception as e:
            logger.warning(f"Failed to save JWT keys to files: {e}, but keys are still usable in memory")
        
        return private_key_pem, public_key_pem
    
    def hash_password(self, password: str) -> str:
        """
        Hash a password using bcrypt.
        
        Since bcrypt has a strict 72-byte limit, we use SHA-256 pre-hashing
        for passwords that are >= 72 bytes to maintain security while staying within limits.
        Note: bcrypt truncates silently at 72 bytes, but we pre-hash to avoid information loss.
        
        We use bcrypt directly instead of passlib to avoid passlib's strict validation
        that throws errors for passwords >= 72 bytes.
        """
        password_bytes = password.encode('utf-8')
        
        # If password is >= 72 bytes, pre-hash it with SHA-256
        # This ensures security while staying within bcrypt's strict limits
        # We use >= instead of > to avoid any edge cases with exact 72-byte passwords
        if len(password_bytes) >= BCRYPT_MAX_PASSWORD_LENGTH:
            # Pre-hash with SHA-256 to get a fixed 64-character hex string (32 bytes)
            password_prehashed = hashlib.sha256(password_bytes).hexdigest()
            # Hash the pre-hashed password with bcrypt directly (64 chars = 64 bytes < 72, safe)
            salt = bcrypt.gensalt()
            hashed_bytes = bcrypt.hashpw(password_prehashed.encode('utf-8'), salt)
            return hashed_bytes.decode('utf-8')
        else:
            # For passwords < 72 bytes, hash directly using bcrypt
            salt = bcrypt.gensalt()
            hashed_bytes = bcrypt.hashpw(password_bytes, salt)
            return hashed_bytes.decode('utf-8')
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """
        Verify a password against its hash.
        
        Handles both directly hashed passwords and pre-hashed passwords.
        Uses bcrypt directly to match the hash_password implementation.
        """
        password_bytes = plain_password.encode('utf-8')
        hashed_bytes = hashed_password.encode('utf-8')
        
        # Try direct verification first (for passwords < 72 bytes)
        if len(password_bytes) < BCRYPT_MAX_PASSWORD_LENGTH:
            try:
                if bcrypt.checkpw(password_bytes, hashed_bytes):
                    return True
            except Exception:
                # If direct verification fails, try pre-hashed verification
                pass
        
        # If direct verification fails or password is >= 72 bytes, try pre-hashed verification
        # This matches the logic in hash_password where we pre-hash passwords >= 72 bytes
        password_prehashed = hashlib.sha256(password_bytes).hexdigest()
        try:
            return bcrypt.checkpw(password_prehashed.encode('utf-8'), hashed_bytes)
        except Exception:
            return False
    
    def create_access_token(self, user_id: str, email: str, additional_claims: Optional[Dict] = None) -> str:
        """Create JWT access token."""
        now = datetime.utcnow()
        expire = now + timedelta(minutes=self.access_token_expire_minutes)
        
        payload = {
            "sub": user_id,
            "email": email,
            "type": "access",
            "iat": now,
            "exp": expire,
            "jti": str(uuid.uuid4())
        }
        
        if additional_claims:
            payload.update(additional_claims)
        
        return jwt.encode(payload, self.private_key, algorithm=self.algorithm)
    
    def create_refresh_token(self, user_id: str, email: str) -> str:
        """Create JWT refresh token."""
        now = datetime.utcnow()
        expire = now + timedelta(days=self.refresh_token_expire_days)
        
        payload = {
            "sub": user_id,
            "email": email,
            "type": "refresh",
            "iat": now,
            "exp": expire,
            "jti": str(uuid.uuid4())
        }
        
        return jwt.encode(payload, self.private_key, algorithm=self.algorithm)
    
    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify and decode JWT token."""
        try:
            payload = jwt.decode(
                token,
                self.public_key,
                algorithms=[self.algorithm],
                options={"verify_exp": True}
            )
            return payload
        except jwt.ExpiredSignatureError:
            logger.warning("Token expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning("Invalid token", error=str(e))
            return None
    
    def get_user_by_email(self, db: Session, email: str) -> Optional[User]:
        """Get user by email address."""
        return db.query(User).filter(User.email == email).first()
    
    def get_user_by_id(self, db: Session, user_id: str) -> Optional[User]:
        """Get user by ID."""
        return db.query(User).filter(User.id == user_id).first()
    
    def create_user(self, db: Session, user_create: UserCreate, ip_address: str = None) -> User:
        """Create a new user account."""
        # Check if user already exists
        existing_user = self.get_user_by_email(db, user_create.email)
        if existing_user:
            raise ValueError("User with this email already exists")
        
        # Hash password
        hashed_password = self.hash_password(user_create.password)
        
        # Create user
        user = User(
            email=user_create.email,
            timezone=user_create.timezone or "UTC",
            language_preference=user_create.language_preference or "en-US"
        )
        
        # Store hashed password (we'll need to add this field to User model)
        user.password_hash = hashed_password
        
        db.add(user)
        db.flush()  # Get user ID
        
        # Create default user settings
        user_settings = UserSettings(
            user_id=user.id,
            whatsapp_opt_in=False,
            voice_training_consent=False,
            calendar_sync_enabled=False,
            privacy_level="standard",
            notification_preferences={}
        )
        
        db.add(user_settings)
        
        # Log user creation
        audit_log = AuditLog(
            user_id=user.id,
            action="user_created",
            resource_type="user",
            resource_id=user.id,
            details={"email": user.email},
            ip_address=ip_address,
            correlation_id=uuid.uuid4()
        )
        
        db.add(audit_log)
        db.commit()
        db.refresh(user)
        
        logger.info("User created", user_id=str(user.id), email=user.email)
        
        return user
    
    def authenticate_user(self, db: Session, email: str, password: str, ip_address: str = None) -> Optional[User]:
        """Authenticate user with email and password."""
        user = self.get_user_by_email(db, email)
        if not user:
            logger.warning("Authentication failed - user not found", email=email)
            return None
        
        if not hasattr(user, 'password_hash') or not self.verify_password(password, user.password_hash):
            logger.warning("Authentication failed - invalid password", user_id=str(user.id))
            
            # Log failed authentication attempt
            audit_log = AuditLog(
                user_id=user.id,
                action="login_failed",
                resource_type="user",
                resource_id=user.id,
                details={"reason": "invalid_password"},
                ip_address=ip_address,
                correlation_id=uuid.uuid4()
            )
            db.add(audit_log)
            db.commit()
            
            return None
        
        # Log successful authentication
        audit_log = AuditLog(
            user_id=user.id,
            action="login_success",
            resource_type="user",
            resource_id=user.id,
            details={},
            ip_address=ip_address,
            correlation_id=uuid.uuid4()
        )
        db.add(audit_log)
        db.commit()
        
        logger.info("User authenticated", user_id=str(user.id), email=user.email)
        
        return user
    
    def create_token_response(self, user: User) -> TokenResponse:
        """Create token response with access and refresh tokens."""
        access_token = self.create_access_token(str(user.id), user.email)
        refresh_token = self.create_refresh_token(str(user.id), user.email)
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=self.access_token_expire_minutes * 60,
            user=UserResponse(
                id=str(user.id),
                email=user.email,
                avatar_url=user.avatar_url,
                timezone=user.timezone,
                language_preference=user.language_preference,
                created_at=user.created_at
            )
        )
    
    def refresh_access_token(self, db: Session, refresh_token: str, ip_address: str = None) -> Optional[TokenResponse]:
        """Refresh access token using refresh token."""
        payload = self.verify_token(refresh_token)
        if not payload or payload.get("type") != "refresh":
            return None
        
        user_id = payload.get("sub")
        user = self.get_user_by_id(db, user_id)
        if not user:
            return None
        
        # Log token refresh
        audit_log = AuditLog(
            user_id=user.id,
            action="token_refreshed",
            resource_type="user",
            resource_id=user.id,
            details={},
            ip_address=ip_address,
            correlation_id=uuid.uuid4()
        )
        db.add(audit_log)
        db.commit()
        
        return self.create_token_response(user)


# Create global auth service instance
auth_service = AuthService()