"""
Authentication API endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
import structlog

from ...database.base import get_db
from ...services.auth import auth_service
from ...schemas.auth import (
    UserCreate, UserLogin, TokenResponse, RefreshTokenRequest,
    UserResponse, PasswordChange, UserSettingsResponse, UserSettingsUpdate,
    UserUpdate
)
from ...database.models import UserSettings

logger = structlog.get_logger(__name__)
security = HTTPBearer()

router = APIRouter()


def get_client_ip(request: Request) -> str:
    """Get client IP address from request."""
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register_user(
    user_create: UserCreate,
    request: Request,
    db: Session = Depends(get_db)
):
    """Register a new user account."""
    try:
        logger.info("Registration request received", email=user_create.email)
        client_ip = get_client_ip(request)
        user = auth_service.create_user(db, user_create, client_ip)
        logger.info("User created successfully", user_id=str(user.id))
        
        token_response = auth_service.create_token_response(user)
        logger.info("Token response created successfully", user_id=str(user.id))
        
        logger.info("User registered successfully", user_id=str(user.id), email=user.email)
        
        return token_response
        
    except ValueError as e:
        logger.warning("User registration failed - validation error", error=str(e), email=getattr(user_create, 'email', 'unknown'))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        logger.error(
            "User registration error", 
            error=str(e), 
            email=getattr(user_create, 'email', 'unknown'), 
            error_type=type(e).__name__,
            traceback=error_trace,
            exc_info=True
        )
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
        client_ip = get_client_ip(request)
        user = auth_service.authenticate_user(
            db, user_login.email, user_login.password, client_ip
        )
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        token_response = auth_service.create_token_response(user)
        
        logger.info("User logged in successfully", user_id=str(user.id), email=user.email)
        
        return token_response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("User login error", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed"
        )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    refresh_request: RefreshTokenRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """Refresh access token using refresh token."""
    try:
        client_ip = get_client_ip(request)
        token_response = auth_service.refresh_access_token(
            db, refresh_request.refresh_token, client_ip
        )
        
        if not token_response:
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


@router.get("/me", response_model=UserResponse)
async def get_current_user(
    request: Request,
    db: Session = Depends(get_db)
):
    """Get current authenticated user information."""
    try:
        # User ID is set by JWT middleware
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
        logger.error("Get current user error", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get user information"
        )


@router.patch("/me", response_model=UserResponse)
async def update_current_user(
    user_update: UserUpdate,
    request: Request,
    db: Session = Depends(get_db)
):
    """Update current authenticated user information."""
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
        
        # Update only provided fields
        update_data = user_update.model_dump(exclude_unset=True)
        
        # Check if email is being updated and if it already exists
        if 'email' in update_data and update_data['email'] != user.email:
            existing_user = auth_service.get_user_by_email(db, update_data['email'])
            if existing_user and str(existing_user.id) != user_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email already in use"
                )
        
        # Validate language_preference if provided
        if 'language_preference' in update_data:
            valid_languages = ['en-US', 'fa-IR', 'ar-UA']
            if update_data['language_preference'] not in valid_languages:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid language preference. Must be one of: {', '.join(valid_languages)}"
                )
        
        # Apply updates
        for key, value in update_data.items():
            setattr(user, key, value)
        
        db.commit()
        db.refresh(user)
        
        logger.info("User profile updated successfully", user_id=user_id)
        
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
        logger.error("Update user profile error", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update user profile"
        )


@router.post("/logout")
async def logout_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """Logout user (invalidate token - placeholder for token blacklisting)."""
    try:
        user_id = getattr(request.state, 'user_id', None)
        if user_id:
            logger.info("User logged out", user_id=user_id)
        
        # In a production system, you would add the token to a blacklist
        # For now, we just return success
        return {"message": "Logged out successfully"}
        
    except Exception as e:
        logger.error("Logout error", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Logout failed"
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
        
        settings = db.query(UserSettings).filter(UserSettings.user_id == user_id).first()
        if not settings:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User settings not found"
            )
        
        return UserSettingsResponse(
            user_id=str(settings.user_id),
            whatsapp_opt_in=settings.whatsapp_opt_in,
            voice_training_consent=settings.voice_training_consent,
            calendar_sync_enabled=settings.calendar_sync_enabled,
            privacy_level=settings.privacy_level,
            notification_preferences=settings.notification_preferences or {}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Get user settings error", error=str(e), exc_info=True)
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
    """Update user settings."""
    try:
        user_id = getattr(request.state, 'user_id', None)
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required"
            )
        
        settings = db.query(UserSettings).filter(UserSettings.user_id == user_id).first()
        if not settings:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User settings not found"
            )
        
        # Update only provided fields
        update_data = settings_update.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(settings, key, value)
        
        db.commit()
        db.refresh(settings)
        
        logger.info("User settings updated successfully", user_id=user_id)
        
        return UserSettingsResponse(
            user_id=str(settings.user_id),
            whatsapp_opt_in=settings.whatsapp_opt_in,
            voice_training_consent=settings.voice_training_consent,
            calendar_sync_enabled=settings.calendar_sync_enabled,
            privacy_level=settings.privacy_level,
            notification_preferences=settings.notification_preferences or {}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Update user settings error", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update user settings"
        )


@router.put("/password", response_model=dict)
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
        
        # Verify current password
        if not auth_service.verify_password(password_change.current_password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect"
            )
        
        # Update password
        user.password_hash = auth_service.hash_password(password_change.new_password)
        db.commit()
        
        logger.info("Password changed successfully", user_id=user_id)
        
        return {"message": "Password changed successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Password change error", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Password change failed"
        )