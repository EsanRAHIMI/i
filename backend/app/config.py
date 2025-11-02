"""
Application configuration using Pydantic settings.
"""
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator
import os


class Settings(BaseSettings):
    """Application settings."""
    
    # Application
    APP_NAME: str = "Intelligent AI Assistant"
    DEBUG: bool = False
    
    # Security
    SECRET_KEY: Optional[str] = None
    JWT_ALGORITHM: str = "RS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # JWT Keys (RS256)
    JWT_PRIVATE_KEY: Optional[str] = None
    JWT_PUBLIC_KEY: Optional[str] = None
    
    # Encryption
    ENCRYPTION_MASTER_KEY: Optional[str] = None
    
    # TLS Configuration
    TLS_CERT_FILE: Optional[str] = None
    TLS_KEY_FILE: Optional[str] = None
    TLS_CA_FILE: Optional[str] = None
    ENABLE_TLS: bool = True
    
    # Key Management
    KEY_ROTATION_ENABLED: bool = True
    JWT_KEY_ROTATION_DAYS: int = 30
    API_KEY_ROTATION_DAYS: int = 90
    
    # Database
    DATABASE_URL: Optional[str] = None
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "intelligent_ai_assistant"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # CORS
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8000", "http://localhost"]
    # ALLOWED_HOSTS supports wildcards, e.g., "*.example.com" or "localhost:*"
    # For local development, we accept localhost with any port
    ALLOWED_HOSTS: List[str] = ["localhost", "127.0.0.1", "0.0.0.0", "localhost:*", "127.0.0.1:*", "0.0.0.0:*"]
    
    # Rate Limiting
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_WINDOW: int = 60  # seconds
    
    # External APIs
    GOOGLE_CLIENT_ID: Optional[str] = None
    GOOGLE_CLIENT_SECRET: Optional[str] = None
    GOOGLE_REDIRECT_URI: Optional[str] = None
    FRONTEND_URL: Optional[str] = "http://localhost:3000"
    WHATSAPP_ACCESS_TOKEN: Optional[str] = None
    WHATSAPP_PHONE_NUMBER_ID: Optional[str] = None
    WHATSAPP_VERIFY_TOKEN: Optional[str] = None
    WHATSAPP_WEBHOOK_SECRET: Optional[str] = None
    
    # Voice Processing
    WHISPER_MODEL_SIZE: str = "base"  # tiny, base, small, medium, large
    ELEVENLABS_API_KEY: Optional[str] = None
    TTS_DEFAULT_LANGUAGE: str = "en"
    TTS_MAX_TEXT_LENGTH: int = 5000
    VOICE_PROCESSING_TIMEOUT: int = 30  # seconds
    
    # Celery
    CELERY_BROKER_URL: Optional[str] = None
    CELERY_RESULT_BACKEND: Optional[str] = None
    
    # Logging
    LOG_LEVEL: str = "INFO"
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )
    
    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v
    
    def get_database_url(self) -> str:
        """Get database URL, constructing from components if not provided."""
        from urllib.parse import quote_plus
        
        # Always construct from components if we have postgres environment variables
        if self.POSTGRES_HOST != "localhost" or self.POSTGRES_USER != "postgres":
            # URL encode the password to handle special characters
            encoded_password = quote_plus(self.POSTGRES_PASSWORD)
            return f"postgresql://{self.POSTGRES_USER}:{encoded_password}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        # Fallback to DATABASE_URL if set and no custom postgres config
        if self.DATABASE_URL:
            return self.DATABASE_URL
        # URL encode the password for fallback case too
        encoded_password = quote_plus(self.POSTGRES_PASSWORD)
        return f"postgresql://{self.POSTGRES_USER}:{encoded_password}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
    
    @field_validator("ALLOWED_HOSTS", mode="before")
    @classmethod
    def parse_allowed_hosts(cls, v):
        if isinstance(v, str):
            return [host.strip() for host in v.split(",")]
        return v
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Set Celery URLs based on Redis URL if not explicitly set
        if not self.CELERY_BROKER_URL:
            self.CELERY_BROKER_URL = self.REDIS_URL.replace('/0', '/1')
        if not self.CELERY_RESULT_BACKEND:
            self.CELERY_RESULT_BACKEND = self.REDIS_URL.replace('/0', '/2')


# Create settings instance
def get_settings() -> Settings:
    """Get application settings."""
    return Settings()

settings = get_settings()