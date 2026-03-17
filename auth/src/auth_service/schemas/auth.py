"""
Authentication schemas.
"""
from datetime import datetime
from typing import Optional
import os
from pydantic import BaseModel, EmailStr, Field, ConfigDict, field_validator, field_serializer


class UserCreate(BaseModel):
    """Schema for user registration."""
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    timezone: Optional[str] = Field(default="UTC")
    language_preference: Optional[str] = Field(default="en-US")
    
    @field_validator("password")
    def validate_password(cls, v):
        """Validate password strength."""
        disable_complexity = os.getenv("AUTH_DISABLE_PASSWORD_COMPLEXITY")
        if disable_complexity and disable_complexity.strip().lower() in {"1", "true", "yes", "on"}:
            return v

        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        
        password_bytes = v.encode('utf-8')
        if len(password_bytes) > 128:
            raise ValueError("Password is too long (maximum 128 bytes)")
        
        has_upper = any(c.isupper() for c in v)
        has_lower = any(c.islower() for c in v)
        has_digit = any(c.isdigit() for c in v)
        has_special = any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in v)
        
        if not all([has_upper, has_lower, has_digit, has_special]):
            raise ValueError(
                "Password must contain at least one uppercase letter, "
                "one lowercase letter, one digit, and one special character"
            )
        
        return v


class UserLogin(BaseModel):
    """Schema for user login."""
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    """Schema for user response data."""
    id: str
    email: str
    avatar_url: Optional[str] = None
    timezone: str
    language_preference: str
    created_at: datetime
    
    @field_serializer('created_at')
    def serialize_datetime(self, dt: datetime, _info):
        """Serialize datetime to ISO format string."""
        return dt.isoformat() if dt else None
    
    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    """Schema for token response."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds
    user: UserResponse


class RefreshTokenRequest(BaseModel):
    """Schema for refresh token request."""
    refresh_token: str


class ForgotPasswordRequest(BaseModel):
    """Schema for requesting a password reset email."""
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    """Schema for resetting password using a reset token."""
    token: str = Field(min_length=10)
    new_password: str = Field(min_length=8, max_length=128)

    @field_validator("new_password")
    def validate_new_password(cls, v):
        disable_complexity = os.getenv("AUTH_DISABLE_PASSWORD_COMPLEXITY")
        if disable_complexity and disable_complexity.strip().lower() in {"1", "true", "yes", "on"}:
            return v

        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")

        password_bytes = v.encode('utf-8')
        if len(password_bytes) > 128:
            raise ValueError("Password is too long (maximum 128 bytes)")

        has_upper = any(c.isupper() for c in v)
        has_lower = any(c.islower() for c in v)
        has_digit = any(c.isdigit() for c in v)
        has_special = any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in v)

        if not all([has_upper, has_lower, has_digit, has_special]):
            raise ValueError(
                "Password must contain at least one uppercase letter, "
                "one lowercase letter, one digit, and one special character"
            )
        
        return v


class PasswordChange(BaseModel):
    """Schema for password change (authenticated user)."""
    current_password: str
    new_password: str = Field(min_length=8, max_length=128)

    @field_validator("new_password")
    def validate_new_password(cls, v):
        disable_complexity = os.getenv("AUTH_DISABLE_PASSWORD_COMPLEXITY")
        if disable_complexity and disable_complexity.strip().lower() in {"1", "true", "yes", "on"}:
            return v

        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")

        password_bytes = v.encode('utf-8')
        if len(password_bytes) > 128:
            raise ValueError("Password is too long (maximum 128 bytes)")

        has_upper = any(c.isupper() for c in v)
        has_lower = any(c.islower() for c in v)
        has_digit = any(c.isdigit() for c in v)
        has_special = any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in v)

        if not all([has_upper, has_lower, has_digit, has_special]):
            raise ValueError(
                "Password must contain at least one uppercase letter, "
                "one lowercase letter, one digit, and one special character"
            )
        
        return v


class UserSettingsResponse(BaseModel):
    """Schema for user settings response."""
    whatsapp_opt_in: bool
    voice_training_consent: bool
    calendar_sync_enabled: bool
    privacy_level: str
    notification_preferences: dict
    
    model_config = ConfigDict(from_attributes=True)


class UserUpdate(BaseModel):
    """Schema for updating user profile."""
    timezone: Optional[str] = None
    language_preference: Optional[str] = None


class UserSettingsUpdate(BaseModel):
    """Schema for updating user settings."""
    whatsapp_opt_in: Optional[bool] = None
    voice_training_consent: Optional[bool] = None
    calendar_sync_enabled: Optional[bool] = None
    privacy_level: Optional[str] = None
    notification_preferences: Optional[dict] = None
