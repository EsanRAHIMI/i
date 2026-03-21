"""
Authentication service for user management.
"""
import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import httpx
from urllib.parse import urlencode
from sqlalchemy.orm import Session

from ..config import settings
from ..database.models import User, UserSettings, PasswordResetToken
from ..schemas.auth import UserCreate, UserResponse, TokenResponse
from ..auth_utils import jwt_manager, hash_password, verify_password
from ..core.token_blacklist import is_refresh_jti_blacklisted


class AuthService:
    """Authentication service."""

    def __init__(self):
        self.jwt_manager = jwt_manager

    def create_user(self, db: Session, user_create: UserCreate, ip_address: str = None) -> User:
        """Create a new user."""
        # Check if user already exists
        existing_user = db.query(User).filter(User.email == user_create.email).first()
        if existing_user:
            raise ValueError("User with this email already exists")

        # Create new user
        hashed_password = hash_password(user_create.password)
        user = User(
            email=user_create.email,
            password_hash=hashed_password,
            timezone=user_create.timezone or "UTC",
            language_preference=user_create.language_preference or "en-US"
        )
        
        db.add(user)
        db.commit()
        db.refresh(user)

        # Create user settings
        user_settings = UserSettings(user_id=user.id)
        db.add(user_settings)
        db.commit()

        return user

    def authenticate_user(self, db: Session, email: str, password: str, ip_address: str = None) -> Optional[User]:
        """Authenticate user with email and password."""
        user = db.query(User).filter(User.email == email).first()
        if not user:
            return None
        
        if not verify_password(password, user.password_hash):
            return None
        
        return user

    def get_user_by_email(self, db: Session, email: str) -> Optional[User]:
        """Get user by email."""
        return db.query(User).filter(User.email == email).first()

    def get_user_by_id(self, db: Session, user_id: str) -> Optional[User]:
        """Get user by ID."""
        return db.query(User).filter(User.id == user_id).first()

    def create_token_response(self, user: User) -> TokenResponse:
        """Create token response for user."""
        access_token = self.jwt_manager.create_access_token(
            user_id=str(user.id),
            email=user.email
        )
        refresh_token = self.jwt_manager.create_refresh_token(
            user_id=str(user.id),
            email=user.email
        )
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
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
        payload = self.jwt_manager.verify_token(refresh_token)
        if not payload:
            return None
        
        if payload.get("type") != "refresh":
            return None

        jti = payload.get("jti")
        if jti and is_refresh_jti_blacklisted(jti):
            return None
        
        user = self.get_user_by_id(db, payload["sub"])
        if not user:
            return None
        
        return self.create_token_response(user)

    def create_password_reset_token(self, db: Session, email: str) -> Optional[str]:
        """Create password reset token for user."""
        user = self.get_user_by_email(db, email)
        if not user:
            return None  # Don't reveal if user exists
        
        # Generate secure token (raw token never stored)
        token = secrets.token_urlsafe(48)
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        
        # Set expiration time
        expires_at = datetime.utcnow() + timedelta(minutes=settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES)
        
        # Create reset token
        reset_token = PasswordResetToken(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=expires_at,
        )
        
        db.add(reset_token)
        db.commit()
        
        return token

    def verify_password_reset_token(self, db: Session, token: str) -> Optional[User]:
        """Verify password reset token and return user."""
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        
        reset_token = db.query(PasswordResetToken).filter(
            PasswordResetToken.token_hash == token_hash,
            PasswordResetToken.used_at.is_(None),
            PasswordResetToken.expires_at > datetime.utcnow(),
        ).first()
        
        if not reset_token:
            return None
        
        user = self.get_user_by_id(db, reset_token.user_id)
        return user

    def reset_password(self, db: Session, token: str, new_password: str) -> bool:
        """Reset user password using token."""
        user = self.verify_password_reset_token(db, token)
        if not user:
            return False
        
        # Update password
        user.password_hash = hash_password(new_password)
        db.commit()
        
        # Mark token as used
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        reset_token = db.query(PasswordResetToken).filter(
            PasswordResetToken.token_hash == token_hash
        ).first()
        if reset_token:
            reset_token.used_at = datetime.utcnow()
            db.commit()
        
        return True

    def change_password(self, db: Session, user: User, current_password: str, new_password: str) -> bool:
        """Change user password (authenticated user)."""
        if not verify_password(current_password, user.password_hash):
            return False
        
        user.password_hash = hash_password(new_password)
        db.commit()
        return True

    def update_user(self, db: Session, user: User, **updates) -> User:
        """Update user profile."""
        for field, value in updates.items():
            if hasattr(user, field) and value is not None:
                setattr(user, field, value)
        
        db.commit()
        db.refresh(user)
        return user

    def update_user_settings(self, db: Session, user: User, **updates) -> UserSettings:
        """Update user settings."""
        settings_obj = db.query(UserSettings).filter(UserSettings.user_id == user.id).first()
        if not settings_obj:
            settings_obj = UserSettings(user_id=user.id)
            db.add(settings_obj)
        
        for field, value in updates.items():
            if hasattr(settings_obj, field) and value is not None:
                setattr(settings_obj, field, value)
        
        db.commit()
        db.refresh(settings_obj)
        return settings_obj

    def get_google_authorize_url(self, state: str) -> str:
        """Generate Google OAuth authorize URL."""
        params = {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "redirect_uri": settings.GOOGLE_REDIRECT_URI,
            "response_type": "code",
            "scope": "openid email profile",
            "access_type": "offline",
            "prompt": "select_account",
            "state": state
        }
        return f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"

    async def exchange_google_code_for_token(self, code: str) -> Dict[str, Any]:
        """Exchange Google auth code for access token."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "client_id": settings.GOOGLE_CLIENT_ID,
                    "client_secret": settings.GOOGLE_CLIENT_SECRET,
                    "code": code,
                    "grant_type": "authorization_code",
                    "redirect_uri": settings.GOOGLE_REDIRECT_URI
                }
            )
            response.raise_for_status()
            return response.json()

    async def get_google_user_info(self, access_token: str) -> Dict[str, Any]:
        """Get user info from Google."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://www.googleapis.com/oauth2/v3/userinfo",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            response.raise_for_status()
            return response.json()

    def get_or_create_google_user(self, db: Session, google_info: Dict[str, Any]) -> User:
        """Get existing user or create a new one from Google profile."""
        email = google_info.get("email")
        if not email:
            raise ValueError("Email not provided by Google")

        user = db.query(User).filter(User.email == email).first()
        
        if not user:
            # Create a passwordless user
            import uuid
            user = User(
                email=email,
                password_hash=f"google_auth_{uuid.uuid4().hex}", # Marker for social auth
                avatar_url=google_info.get("picture"),
                timezone="UTC",
                language_preference="en-US"
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            
            # Create default settings
            user_settings = UserSettings(user_id=user.id)
            db.add(user_settings)
            db.commit()
        else:
            # Update avatar if changed
            if google_info.get("picture") and not user.avatar_url:
                user.avatar_url = google_info.get("picture")
                db.commit()
                
        return user


# Global auth service instance
auth_service = AuthService()
