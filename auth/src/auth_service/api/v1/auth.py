"""
Authentication API v1 endpoints.
"""
import os
import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional
from urllib.parse import urlsplit

import boto3
from botocore.exceptions import ClientError
from fastapi import APIRouter, HTTPException, Depends, Request, File, UploadFile, status
from fastapi.responses import FileResponse
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import structlog
import httpx
from pydantic import BaseModel

from ...database.base import get_db
from ...services.auth import auth_service
from ...config import settings
from ...database.models import User, UserSettings, UserAvatar
from ...auth_utils import jwt_manager
from ...core.token_blacklist import blacklist_refresh_jti
from ...schemas.auth import (
    UserCreate, UserLogin, UserResponse, TokenResponse,
    RefreshTokenRequest, ForgotPasswordRequest, ResetPasswordRequest,
    PasswordChange, UserSettingsResponse, UserUpdate, UserSettingsUpdate
)

logger = structlog.get_logger(__name__)

router = APIRouter()


class LogoutRequest(BaseModel):
    refresh_token: Optional[str] = None


class AvatarSelectRequest(BaseModel):
    avatar_url: str

# Avatar upload configuration
_DEFAULT_AVATAR_UPLOAD_DIR = Path(__file__).resolve().parents[4] / "uploads" / "avatars"
AVATAR_UPLOAD_DIR = Path(os.getenv("AVATAR_UPLOAD_DIR", str(_DEFAULT_AVATAR_UPLOAD_DIR)))
AVATAR_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/jpg", "image/png", "image/gif", "image/webp"}
MAX_AVATAR_SIZE = 5 * 1024 * 1024  # 5MB


def _sanitize_username(username: str) -> str:
    username = (username or "").strip().lower()
    username = re.sub(r"[^a-z0-9._-]+", "-", username)
    username = re.sub(r"-+", "-", username).strip("-.")
    return username or "user"


def _username_for_user(user: User) -> str:
    email = (getattr(user, "email", None) or "").strip()
    local = email.split("@", 1)[0] if "@" in email else email
    return _sanitize_username(local)


def _s3_bucket_name() -> Optional[str]:
    bucket = settings.BUCKET_NAME or os.getenv("BUCKET_NAME")
    return bucket.strip() if isinstance(bucket, str) and bucket.strip() else None


def _s3_prefix() -> str:
    prefix = settings.S3_PREFIX or os.getenv("S3_PREFIX") or "avatars"
    prefix = prefix.strip().strip("/")
    return prefix or "avatars"


def _s3_key_for_user_id_filename(user_id: str, filename: str) -> str:
    user_id = (user_id or "").strip()
    return f"{_s3_prefix()}/{user_id}/{filename}"


def _s3_user_id_from_filename(filename: str) -> Optional[str]:
    # We generate filenames as <user_id>_<random>.<ext>
    if not isinstance(filename, str) or "_" not in filename:
        return None
    candidate = filename.split("_", 1)[0]
    try:
        uuid.UUID(candidate)
        return candidate
    except Exception:
        return None


def _s3_key_for_filename(filename: str) -> str:
    user_id = _s3_user_id_from_filename(filename)
    if user_id:
        return f"{_s3_prefix()}/{user_id}/{filename}"
    return f"{_s3_prefix()}/{filename}"


def _s3_legacy_key_for_filename(filename: str) -> str:
    # Backward compatibility for objects stored as avatars/<filename>
    return f"{_s3_prefix()}/{filename}"


def _cloudfront_base_url() -> Optional[str]:
    base = settings.CLOUDFRONT_BASE_URL or os.getenv("CLOUDFRONT_BASE_URL")
    if not isinstance(base, str) or not base.strip():
        return None
    return base.strip().rstrip("/")


def _cloudfront_url_for_s3_key(s3_key: str) -> Optional[str]:
    base = _cloudfront_base_url()
    if not base:
        return None
    key = (s3_key or "").lstrip("/")
    return f"{base}/{key}" if key else None


def _is_local_host(hostname: Optional[str]) -> bool:
    return hostname in {"localhost", "127.0.0.1"}


def _avatar_url_for_filename(filename: str, request: Optional[Request]) -> str:
    is_local_request = bool(request and _is_local_host(request.url.hostname))
    cloudfront_base = _cloudfront_base_url()
    if cloudfront_base and not is_local_request:
        return f"{cloudfront_base}/{_s3_key_for_filename(filename)}"
    if settings.AUTH_PUBLIC_BASE_URL and not is_local_request:
        return f"{settings.AUTH_PUBLIC_BASE_URL.rstrip('/')}/v1/auth/avatar/{filename}"
    return f"/v1/auth/avatar/{filename}"


def _extract_avatar_filename(avatar_url: str) -> Optional[str]:
    if not isinstance(avatar_url, str) or not avatar_url.strip():
        return None
    url = avatar_url.strip()
    try:
        parsed = urlsplit(url)
        path = parsed.path if parsed.scheme in {"http", "https"} else url
    except Exception:
        path = url

    if path.startswith("/api/v1/auth/avatar/"):
        path = path.replace("/api/v1/auth/avatar/", "/v1/auth/avatar/")
    if path.startswith("/v1/avatar/"):
        path = path.replace("/v1/avatar/", "/v1/auth/avatar/")

    # Accept either /v1/auth/avatar/<filename> or /avatars/<filename>
    if "/v1/auth/avatar/" in path:
        return path.split("/v1/auth/avatar/")[-1].split("/")[-1]
    return path.split("/")[-1] if "/" in path else path


def _get_s3_client():
    # Relies on AWS_ACCESS_KEY_ID/AWS_SECRET_ACCESS_KEY env vars (or IAM role in production)
    region = settings.AWS_REGION or os.getenv("AWS_REGION")
    access_key = settings.AWS_ACCESS_KEY_ID or os.getenv("AWS_ACCESS_KEY_ID")
    secret_key = settings.AWS_SECRET_ACCESS_KEY or os.getenv("AWS_SECRET_ACCESS_KEY")
    if access_key and secret_key:
        return boto3.client(
            "s3",
            region_name=region,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
        )
    return boto3.client("s3", region_name=region)


def get_client_ip(request: Request) -> str:
    """Get client IP address."""
    return request.client.host if request.client else "unknown"


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register_user(
    user_create: UserCreate,
    request: Request,
    db: Session = Depends(get_db)
):
    """Register a new user."""
    try:
        ip_address = get_client_ip(request)
        user = auth_service.create_user(db, user_create, ip_address)
        
        logger.info("User registered successfully", user_id=str(user.id), email=user.email)
        
        return auth_service.create_token_response(user)
        
    except ValueError as e:
        logger.warning("Registration failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error("Registration error", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed"
        )


@router.post("/login", response_model=TokenResponse)
async def login_user(
    user_login: UserLogin,
    request: Request,
    db: Session = Depends(get_db)
):
    """Authenticate user and return tokens."""
    try:
        ip_address = get_client_ip(request)
        user = auth_service.authenticate_user(db, user_login.email, user_login.password, ip_address)
        
        if not user:
            logger.warning("Login failed", email=user_login.email)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        logger.info("User logged in successfully", user_id=str(user.id), email=user.email)
        
        return auth_service.create_token_response(user)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Login error", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed"
        )


@router.get("/google/authorize")
async def google_authorize(request: Request):
    """Initiate Google OAuth flow by returning the authorization URL."""
    state = str(uuid.uuid4())
    # You might want to save the state in a cookie/session or redis to verify in callback
    auth_url = auth_service.get_google_authorize_url(state=state)
    logger.info("Initiating Google OAuth flow", state=state)
    return {"authorization_url": auth_url, "state": state}


class GoogleCallbackRequest(BaseModel):
    code: str
    state: Optional[str] = None


@router.post("/google/callback", response_model=TokenResponse)
async def google_callback(
    body: GoogleCallbackRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """Handle Google OAuth callback and log in user."""
    try:
        # 1. Exchange code for tokens
        token_data = await auth_service.exchange_google_code_for_token(body.code)
        
        # 2. Get user info
        google_info = await auth_service.get_google_user_info(token_data["access_token"])
        
        # 3. Get or create user in our DB
        user = auth_service.get_or_create_google_user(db, google_info)
        
        logger.info("Google OAuth login successful", user_id=str(user.id), email=user.email)
        
        # 4. Return our own JWT token response
        return auth_service.create_token_response(user)
        
    except httpx.HTTPStatusError as e:
        logger.error("Google OAuth API error", error=str(e), status_code=e.response.status_code)
        raise HTTPException(status_code=400, detail="Failed to authenticate with Google")
    except Exception as e:
        logger.error("Google OAuth internal error", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Authentication failed")


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    refresh_request: RefreshTokenRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """Refresh access token."""
    try:
        ip_address = get_client_ip(request)
        token_response = auth_service.refresh_access_token(db, refresh_request.refresh_token, ip_address)
        
        if not token_response:
            logger.warning("Token refresh failed")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token"
            )
        
        logger.info("Token refreshed successfully", user_id=token_response.user.id)
        
        return token_response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Token refresh error", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token refresh failed"
        )


@router.post("/logout")
async def logout_user(body: LogoutRequest, request: Request):
    """Logout user; optionally blacklist refresh token."""
    user_id = getattr(request.state, 'user_id', None)
    
    if body and body.refresh_token:
        payload = jwt_manager.verify_token(body.refresh_token)
        if payload and payload.get("type") == "refresh":
            jti = payload.get("jti")
            exp = payload.get("exp")
            if jti and exp:
                try:
                    ttl = max(0, int(exp) - int(datetime.utcnow().timestamp()))
                except Exception:
                    ttl = 0
                if ttl > 0:
                    blacklist_refresh_jti(jti, ttl_seconds=ttl)
    
    logger.info("User logged out", user_id=user_id)
    return {"message": "Logged out successfully"}


@router.get("/me", response_model=UserResponse)
async def get_current_user(
    request: Request,
    db: Session = Depends(get_db)
):
    """Get current user profile."""
    try:
        user_id = getattr(request.state, 'user_id', None)
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required"
            )
        
        user = auth_service.get_user_by_id(db, user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # Normalize legacy avatar URLs and avoid returning broken avatar paths
        if user.avatar_url:
            normalized_avatar_url = user.avatar_url

            # If stored as absolute URL (CloudFront/S3), keep it as-is.
            # Frontend can load absolute URLs directly, and rewriting to local paths
            # breaks S3-backed avatars (it also triggered local filesystem checks).
            try:
                parsed = urlsplit(normalized_avatar_url)
                if parsed.scheme in {"http", "https"}:
                    parsed = None
            except Exception:
                parsed = None

            if normalized_avatar_url.startswith("/api/v1/auth/avatar/"):
                normalized_avatar_url = normalized_avatar_url.replace(
                    "/api/v1/auth/avatar/",
                    "/v1/auth/avatar/",
                )

            if normalized_avatar_url.startswith("/v1/avatar/"):
                normalized_avatar_url = normalized_avatar_url.replace(
                    "/v1/avatar/",
                    "/v1/auth/avatar/",
                )

            if normalized_avatar_url.startswith("/v1/auth/avatar/"):
                filename = normalized_avatar_url.split("/")[-1]
                if filename:
                    bucket = _s3_bucket_name()
                    if bucket:
                        # S3-backed: validate against DB history rather than local filesystem.
                        exists = (
                            db.query(UserAvatar.id)
                            .filter(UserAvatar.user_id == user_id, UserAvatar.filename == filename)
                            .first()
                        )
                        if not exists:
                            normalized_avatar_url = None
                    else:
                        # Local-only: keep legacy behavior
                        avatar_path = AVATAR_UPLOAD_DIR / filename
                        if not avatar_path.exists():
                            normalized_avatar_url = None

            if normalized_avatar_url != user.avatar_url:
                user.avatar_url = normalized_avatar_url
                db.commit()

        return UserResponse(
            id=str(user.id),
            email=user.email,
            avatar_url=user.avatar_url,
            timezone=user.timezone,
            language_preference=user.language_preference,
            created_at=user.created_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Get user error", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get user profile"
        )


@router.patch("/me", response_model=UserResponse)
async def update_current_user(
    user_update: UserUpdate,
    request: Request,
    db: Session = Depends(get_db)
):
    """Update current user profile."""
    try:
        user_id = getattr(request.state, 'user_id', None)
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required"
            )
        
        user = auth_service.get_user_by_id(db, user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Update user
        updates = user_update.model_dump(exclude_unset=True)
        updated_user = auth_service.update_user(db, user, **updates)
        
        logger.info("User profile updated", user_id=str(user.id))
        
        return UserResponse(
            id=str(updated_user.id),
            email=updated_user.email,
            avatar_url=updated_user.avatar_url,
            timezone=updated_user.timezone,
            language_preference=updated_user.language_preference,
            created_at=updated_user.created_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Update user error", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update user profile"
        )


@router.get("/settings", response_model=UserSettingsResponse)
async def get_user_settings(
    request: Request,
    db: Session = Depends(get_db)
):
    """Get current user settings."""
    try:
        user_id = getattr(request.state, 'user_id', None)
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required"
            )
        
        user = auth_service.get_user_by_id(db, user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        settings_obj = db.query(UserSettings).filter(UserSettings.user_id == user_id).first()
        if not settings_obj:
            settings_obj = UserSettings(user_id=user_id)
            db.add(settings_obj)
            db.commit()
        
        return UserSettingsResponse(
            whatsapp_opt_in=settings_obj.whatsapp_opt_in,
            voice_training_consent=settings_obj.voice_training_consent,
            calendar_sync_enabled=settings_obj.calendar_sync_enabled,
            privacy_level=settings_obj.privacy_level,
            notification_preferences=settings_obj.notification_preferences or {}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Get settings error", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get user settings"
        )


@router.patch("/settings", response_model=UserSettingsResponse)
async def update_user_settings(
    settings_update: UserSettingsUpdate,
    request: Request,
    db: Session = Depends(get_db)
):
    """Update current user settings."""
    try:
        user_id = getattr(request.state, 'user_id', None)
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required"
            )
        
        user = auth_service.get_user_by_id(db, user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Update settings
        updates = settings_update.model_dump(exclude_unset=True)
        updated_settings = auth_service.update_user_settings(db, user, **updates)
        
        logger.info("User settings updated", user_id=str(user.id))
        
        return UserSettingsResponse(
            whatsapp_opt_in=updated_settings.whatsapp_opt_in,
            voice_training_consent=updated_settings.voice_training_consent,
            calendar_sync_enabled=updated_settings.calendar_sync_enabled,
            privacy_level=updated_settings.privacy_level,
            notification_preferences=updated_settings.notification_preferences or {}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Update settings error", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update user settings"
        )


@router.put("/password")
async def change_password(
    password_change: PasswordChange,
    request: Request,
    db: Session = Depends(get_db)
):
    """Change user password."""
    try:
        user_id = getattr(request.state, 'user_id', None)
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required"
            )
        
        user = auth_service.get_user_by_id(db, user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        success = auth_service.change_password(
            db, user, password_change.current_password, password_change.new_password
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect"
            )
        
        logger.info("Password changed successfully", user_id=str(user_id))
        
        return {"message": "Password changed successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Password change error", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Password change failed"
        )


@router.post("/forgot-password")
async def forgot_password(
    forgot_request: ForgotPasswordRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """Request password reset email."""
    try:
        token = auth_service.create_password_reset_token(db, forgot_request.email)
        
        if token:
            # TODO: Send email with reset link
            reset_link = f"{settings.FRONTEND_URL}/reset-password?token={token}"
            logger.info("Password reset token created", email=forgot_request.email)
            # In production, implement email sending here
            if not settings.SMTP_HOST:
                # Development mode: log the reset link
                logger.info("Development mode - reset link", reset_link=reset_link)
        
        # Always return success to prevent email enumeration
        return {"message": "If an account with this email exists, a password reset link has been sent"}
        
    except Exception as e:
        logger.error("Forgot password error", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process password reset request"
        )


@router.post("/reset-password")
async def reset_password(
    reset_request: ResetPasswordRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """Reset password using token."""
    try:
        success = auth_service.reset_password(db, reset_request.token, reset_request.new_password)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired reset token"
            )
        
        logger.info("Password reset successful")
        
        return {"message": "Password reset successful"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Reset password error", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to reset password"
        )


@router.post("/avatar/upload", response_model=UserResponse)
async def upload_avatar(
    file: UploadFile = File(...),
    request: Request = None,
    db: Session = Depends(get_db)
):
    """Upload avatar image for current user."""
    try:
        user_id = getattr(request.state, 'user_id', None)
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required"
            )
        
        user = auth_service.get_user_by_id(db, user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Validate file type
        if file.content_type not in ALLOWED_IMAGE_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid file type. Allowed types: {', '.join(ALLOWED_IMAGE_TYPES)}"
            )
        
        # Read file content
        content = await file.read()
        
        # Validate file size
        if len(content) > MAX_AVATAR_SIZE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File too large. Maximum size: {MAX_AVATAR_SIZE / (1024 * 1024)}MB"
            )
        
        # Generate unique filename
        file_extension = Path(file.filename).suffix if file.filename else ".jpg"
        if not file_extension:
            file_extension = ".jpg"
        
        avatar_filename = f"{user_id}_{uuid.uuid4().hex}{file_extension}"
        bucket = _s3_bucket_name()
        s3_key: Optional[str] = None
        public_url: Optional[str] = None
        if bucket:
            s3_key = _s3_key_for_user_id_filename(str(user_id), avatar_filename)
            s3 = _get_s3_client()
            try:
                s3.put_object(
                    Bucket=bucket,
                    Key=s3_key,
                    Body=content,
                    ContentType=file.content_type or "application/octet-stream",
                    CacheControl="public, max-age=31536000",
                )
                s3.head_object(Bucket=bucket, Key=s3_key)
            except ClientError as e:
                logger.error("S3 avatar upload failed", error=str(e), bucket=bucket, key=s3_key)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to upload avatar"
                )

            public_url = _cloudfront_url_for_s3_key(s3_key)
        else:
            avatar_path = AVATAR_UPLOAD_DIR / avatar_filename
            
            # Save file
            with open(avatar_path, "wb") as f:
                f.write(content)
        
        avatar_url = public_url or _avatar_url_for_filename(avatar_filename, request)
        
        # Intentionally do not delete old avatars to allow avatar history/selection.
        
        # Update user avatar URL
        user.avatar_url = avatar_url

        # Persist avatar metadata for history/selection
        try:
            avatar_row = UserAvatar(
                user_id=user_id,
                filename=avatar_filename,
                s3_key=s3_key,
                public_url=public_url,
                content_type=file.content_type,
                size=len(content),
            )
            db.add(avatar_row)
        except Exception:
            # Don't block upload if history insert fails
            pass
        db.commit()
        db.refresh(user)
        
        logger.info("Avatar uploaded successfully", user_id=user_id, avatar_url=avatar_url)
        
        return UserResponse(
            id=str(user.id),
            email=user.email,
            avatar_url=user.avatar_url,
            timezone=user.timezone,
            language_preference=user.language_preference,
            created_at=user.created_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Avatar upload error", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload avatar"
        )


@router.get("/avatar/{filename}")
async def get_avatar(filename: str, db: Session = Depends(get_db)):
    """Get avatar image file."""
    try:
        if (
            not filename
            or "/" in filename
            or "\\" in filename
            or ".." in filename
            or not re.fullmatch(r"[A-Za-z0-9._-]+", filename)
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid filename"
            )

        bucket = _s3_bucket_name()
        if bucket:
            s3_key = None
            row = (
                db.query(UserAvatar)
                .filter(UserAvatar.filename == filename)
                .order_by(UserAvatar.created_at.desc())
                .first()
            )
            if row and row.s3_key:
                s3_key = row.s3_key
            else:
                s3_key = _s3_key_for_filename(filename)
            s3 = _get_s3_client()
            try:
                try:
                    obj = s3.get_object(Bucket=bucket, Key=s3_key)
                except ClientError as e:
                    code = (e.response or {}).get("Error", {}).get("Code")
                    if code in {"NoSuchKey", "404", "NotFound"}:
                        obj = s3.get_object(Bucket=bucket, Key=_s3_legacy_key_for_filename(filename))
                    else:
                        raise
                body = obj["Body"]
                content_type = obj.get("ContentType") or "application/octet-stream"

                headers = {
                    "Cache-Control": obj.get("CacheControl") or "public, max-age=31536000",
                }

                return StreamingResponse(
                    content=body,
                    media_type=content_type,
                    headers=headers,
                )
            except ClientError as e:
                code = (e.response or {}).get("Error", {}).get("Code")
                if code in {"NoSuchKey", "404", "NotFound"}:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Avatar not found"
                    )
                logger.error("S3 avatar retrieval failed", error=str(e), bucket=bucket, key=s3_key)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to retrieve avatar"
                )

        avatar_path = AVATAR_UPLOAD_DIR / filename
        
        if not avatar_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Avatar not found"
            )
        
        # Determine content type based on file extension
        content_type = "image/jpeg"
        if filename.lower().endswith('.png'):
            content_type = "image/png"
        elif filename.lower().endswith('.gif'):
            content_type = "image/gif"
        elif filename.lower().endswith('.webp'):
            content_type = "image/webp"
        
        return FileResponse(
            path=avatar_path,
            media_type=content_type,
            filename=filename
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Avatar retrieval failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve avatar"
        )


@router.get("/avatar/list")
@router.get("/avatar/list/")
async def list_avatars(request: Request, db: Session = Depends(get_db)):
    """List previously uploaded avatars for the current user."""
    try:
        user_id = getattr(request.state, "user_id", None)
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required"
            )

        results = []
        rows = (
            db.query(UserAvatar)
            .filter(UserAvatar.user_id == user_id)
            .order_by(UserAvatar.created_at.desc())
            .limit(200)
            .all()
        )
        for row in rows:
            results.append(
                {
                    "id": str(row.id),
                    "filename": row.filename,
                    "avatar_url": row.public_url or _avatar_url_for_filename(row.filename, request),
                    "last_modified": row.created_at,
                    "size": row.size,
                }
            )

        return {"items": results}

    except HTTPException:
        raise
    except ClientError as e:
        logger.error("Avatar list failed", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list avatars"
        )


@router.delete("/avatar/history/{avatar_id}", response_model=UserResponse)
@router.delete("/avatar/history/{avatar_id}/", response_model=UserResponse)
async def delete_avatar(
    avatar_id: str,
    request: Request,
    db: Session = Depends(get_db),
):
    """Delete a previously uploaded avatar (DB + S3)."""
    try:
        user_id = getattr(request.state, "user_id", None)
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
            )

        user = auth_service.get_user_by_id(db, user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        avatar_pk = avatar_id
        try:
            avatar_pk = uuid.UUID(str(avatar_id))
        except Exception:
            avatar_pk = avatar_id

        row = (
            db.query(UserAvatar)
            .filter(UserAvatar.id == avatar_pk, UserAvatar.user_id == user_id)
            .first()
        )
        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Avatar not found",
            )

        bucket = _s3_bucket_name()
        if bucket and row.s3_key:
            s3 = _get_s3_client()
            try:
                s3.delete_object(Bucket=bucket, Key=row.s3_key)
            except ClientError as e:
                code = (e.response or {}).get("Error", {}).get("Code")
                if code not in {"NoSuchKey", "404", "NotFound"}:
                    raise
        else:
            avatar_path = AVATAR_UPLOAD_DIR / row.filename
            try:
                if avatar_path.exists():
                    avatar_path.unlink()
            except Exception:
                pass

        deleted_public_url = row.public_url
        deleted_filename = row.filename

        db.delete(row)
        db.commit()

        current = (user.avatar_url or "")
        is_current_deleted = False
        if deleted_public_url and current == deleted_public_url:
            is_current_deleted = True
        if current.startswith("/v1/auth/avatar/") and deleted_filename and current.endswith(f"/{deleted_filename}"):
            is_current_deleted = True

        if is_current_deleted:
            latest = (
                db.query(UserAvatar)
                .filter(UserAvatar.user_id == user_id)
                .order_by(UserAvatar.created_at.desc())
                .first()
            )
            if latest:
                user.avatar_url = latest.public_url or _avatar_url_for_filename(latest.filename, request)
            else:
                user.avatar_url = None
            db.commit()
            db.refresh(user)

        return UserResponse(
            id=str(user.id),
            email=user.email,
            avatar_url=user.avatar_url,
            timezone=user.timezone,
            language_preference=user.language_preference,
            created_at=user.created_at,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Avatar delete failed", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete avatar",
        )


@router.post("/avatar/select", response_model=UserResponse)
@router.post("/avatar/select/", response_model=UserResponse)
async def select_avatar(
    payload: AvatarSelectRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """Select a previously uploaded avatar as the current avatar."""
    try:
        user_id = getattr(request.state, "user_id", None)
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required"
            )

        user = auth_service.get_user_by_id(db, user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        filename = _extract_avatar_filename(payload.avatar_url)
        if not filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid avatar_url"
            )

        if (
            not filename
            or "/" in filename
            or "\\" in filename
            or ".." in filename
            or not re.fullmatch(r"[A-Za-z0-9._-]+", filename)
            or not filename.startswith(f"{user_id}_")
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid filename"
            )

        # Ensure this avatar exists in DB and belongs to the user
        exists = (
            db.query(UserAvatar)
            .filter(UserAvatar.user_id == user_id, UserAvatar.filename == filename)
            .order_by(UserAvatar.created_at.desc())
            .first()
        )
        if not exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Avatar not found"
            )

        user.avatar_url = exists.public_url or _avatar_url_for_filename(filename, request)
        db.commit()
        db.refresh(user)

        return UserResponse(
            id=str(user.id),
            email=user.email,
            avatar_url=user.avatar_url,
            timezone=user.timezone,
            language_preference=user.language_preference,
            created_at=user.created_at,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Avatar select failed", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to select avatar"
        )
