"""
Authentication utilities.
"""
import jwt
import secrets
import hashlib
import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple
from pathlib import Path
import os
import base64
import bcrypt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend

BCRYPT_MAX_PASSWORD_LENGTH = 72


def _normalize_pem_input(value: str) -> bytes:
    if not value:
        return b""
    
    raw = value.strip()
    # Remove surrounding quotes if any
    if (raw.startswith("\"") and raw.endswith("\"")) or (raw.startswith("'") and raw.endswith("'")):
        raw = raw[1:-1].strip()
        
    # Handle escaped newlines
    if "\\n" in raw:
        raw = raw.replace("\\n", "\n")
    
    # If it's already a proper PEM, just return it
    if "-----BEGIN" in raw and "-----END" in raw:
        # Ensure it has actual newlines
        # Some env parsers replace newlines with spaces or just remove them
        if "\n" not in raw:
            # Try to fix it by identifying headers/footers
            parts = raw.split("-----")
            if len(parts) >= 5:
                # parts[1] is BEGIN ..., parts[2] is the body, parts[3] is END ...
                header = f"-----{parts[1]}-----"
                footer = f"-----{parts[3]}-----"
                body = parts[2].strip().replace(" ", "").replace("\r", "")
                # PEM body should be wrapped, but many parsers handle it on one line if it's clean
                return f"{header}\n{body}\n{footer}".encode("utf-8")
        return raw.encode("utf-8")
        
    # If it's just the base64 part, wrap it in headers (assuming RSA/PKCS8 as default)
    try:
        # Check if it's base64
        base64.b64decode(raw, validate=True)
        # We don't know if it's private or public, so we can't easily wrap it here
        # But usually if it's raw base64, we just encode it
        return raw.encode("utf-8")
    except Exception:
        pass
        
    return raw.encode("utf-8")


def _validate_keys(private_pem: bytes, public_pem: bytes) -> None:
    serialization.load_pem_private_key(private_pem, password=None, backend=default_backend())
    serialization.load_pem_public_key(public_pem, backend=default_backend())


def hash_password(password: str) -> str:
    """Hash password compatible with backend (bcrypt + sha256 prehash for >=72 bytes)."""
    password_bytes = password.encode("utf-8")
    if len(password_bytes) >= BCRYPT_MAX_PASSWORD_LENGTH:
        password_prehashed = hashlib.sha256(password_bytes).hexdigest()
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password_prehashed.encode("utf-8"), salt).decode("utf-8")
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password_bytes, salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password compatible with backend (tries direct, then sha256-prehash)."""
    password_bytes = plain_password.encode("utf-8")
    hashed_bytes = hashed_password.encode("utf-8")
    if len(password_bytes) < BCRYPT_MAX_PASSWORD_LENGTH:
        try:
            if bcrypt.checkpw(password_bytes, hashed_bytes):
                return True
        except Exception:
            pass
    password_prehashed = hashlib.sha256(password_bytes).hexdigest()
    try:
        return bcrypt.checkpw(password_prehashed.encode("utf-8"), hashed_bytes)
    except Exception:
        return False


class JWTManager:
    """JWT token manager."""
    
    def __init__(self):
        self.private_key = None
        self.public_key = None
        self.algorithm = "RS256"
        self._load_keys()
    
    def _load_keys(self) -> None:
        """Load JWT keys from environment or files."""
        auth_root = Path(__file__).resolve().parents[2]

        def _resolve_path(path_str: str) -> Path:
            p = Path(path_str)
            if p.is_absolute():
                return p
            return auth_root / p

        # 1) Explicit env keys
        private_key = os.getenv("JWT_PRIVATE_KEY")
        public_key = os.getenv("JWT_PUBLIC_KEY")
        if private_key and public_key:
            _validate_keys(_normalize_pem_input(private_key), _normalize_pem_input(public_key))
            self.private_key = private_key
            self.public_key = public_key
            return

        # 2) Explicit key files
        private_file = os.getenv("JWT_PRIVATE_KEY_FILE")
        public_file = os.getenv("JWT_PUBLIC_KEY_FILE")
        if private_file and public_file:
            private_path = _resolve_path(private_file)
            public_path = _resolve_path(public_file)
        else:
            private_path = None
            public_path = None
        if private_path and public_path and private_path.exists() and public_path.exists():
            private_text = private_path.read_text(encoding="utf-8")
            public_text = public_path.read_text(encoding="utf-8")
            _validate_keys(_normalize_pem_input(private_text), _normalize_pem_input(public_text))
            self.private_key = private_text
            self.public_key = public_text
            return

        # 3) Keys dir with backend-compatible file names
        keys_dir = os.getenv("JWT_KEYS_DIR", "keys")
        keys_dir_path = _resolve_path(keys_dir)
        private_path = keys_dir_path / "jwt_private_key.pem"
        public_path = keys_dir_path / "jwt_public_key.pem"
        if private_path.exists() and public_path.exists():
            private_text = private_path.read_text(encoding="utf-8")
            public_text = public_path.read_text(encoding="utf-8")
            _validate_keys(_normalize_pem_input(private_text), _normalize_pem_input(public_text))
            self.private_key = private_text
            self.public_key = public_text
            return

        # 4) Legacy names (private.pem/public.pem)
        legacy_private = keys_dir_path / "private.pem"
        legacy_public = keys_dir_path / "public.pem"
        if legacy_private.exists() and legacy_public.exists():
            private_text = legacy_private.read_text(encoding="utf-8")
            public_text = legacy_public.read_text(encoding="utf-8")
            _validate_keys(_normalize_pem_input(private_text), _normalize_pem_input(public_text))
            self.private_key = private_text
            self.public_key = public_text
            return

        if os.getenv("JWT_KEYS_REQUIRED", "false").lower() == "true":
            raise ValueError("JWT keys not found and JWT_KEYS_REQUIRED is true")

        self._generate_keys()
    
    def _generate_keys(self) -> None:
        """Generate RSA keys for development."""
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.backends import default_backend
        
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=default_backend()
        )
        
        self.private_key = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        ).decode()
        
        public_key = private_key.public_key()
        self.public_key = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ).decode()
        
        # Save to files if directory exists
        auth_root = Path(__file__).resolve().parents[2]
        keys_dir = os.getenv("JWT_KEYS_DIR", "keys")
        keys_dir_path = (Path(keys_dir) if Path(keys_dir).is_absolute() else auth_root / Path(keys_dir))
        if keys_dir_path.exists():
            with open(keys_dir_path / "private.pem", "w") as f:
                f.write(self.private_key)
            with open(keys_dir_path / "public.pem", "w") as f:
                f.write(self.public_key)
    
    def create_access_token(
        self, 
        user_id: str, 
        email: str, 
        expires_delta: Optional[timedelta] = None,
        additional_claims: Optional[Dict[str, Any]] = None
    ) -> str:
        """Create JWT access token."""
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "30")))
        
        to_encode = {
            "sub": user_id,
            "email": email,
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "access"
        }
        
        if additional_claims:
            to_encode.update(additional_claims)
        
        return jwt.encode(to_encode, self.private_key, algorithm=self.algorithm)
    
    def create_refresh_token(
        self, 
        user_id: str, 
        email: str,
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """Create JWT refresh token."""
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(days=int(os.getenv("JWT_REFRESH_TOKEN_EXPIRE_DAYS", "7")))
        
        to_encode = {
            "sub": user_id,
            "email": email,
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "refresh",
            "jti": uuid.uuid4().hex,
        }
        
        return jwt.encode(to_encode, self.private_key, algorithm=self.algorithm)
    
    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify JWT token."""
        try:
            payload = jwt.decode(token, self.public_key, algorithms=[self.algorithm])
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None
    
    def get_public_key(self) -> str:
        """Get the public key."""
        return self.public_key


# Global instance
jwt_manager = JWTManager()
