"""
TracLearn API Configuration
Settings management using Pydantic
"""

from typing import List, Optional, Union
from pydantic_settings import BaseSettings
from pydantic import AnyHttpUrl, validator


class Settings(BaseSettings):
    """Application settings"""
    
    # Basic settings
    PROJECT_NAME: str = "TracLearn API"
    VERSION: str = "0.1.0"
    API_V1_STR: str = "/api/v1"
    
    # Server settings
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    
    # Security
    SECRET_KEY: str = "your-secret-key-here-change-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8  # 8 days
    
    # Database
    TRAC_CONF_PATH: str = "/path/to/trac.ini"
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20
    
    # CORS
    BACKEND_CORS_ORIGINS: List[AnyHttpUrl] = []
    
    @validator("BACKEND_CORS_ORIGINS", pre=True)
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> Union[List[str], str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)
    
    # Redis (for caching)
    REDIS_URL: Optional[str] = "redis://localhost:6379/0"
    CACHE_TTL: int = 3600  # 1 hour
    
    # AI/ML Settings
    OPENAI_API_KEY: Optional[str] = None
    AI_MODEL: str = "gpt-3.5-turbo"
    AI_TEMPERATURE: float = 0.7
    AI_MAX_TOKENS: int = 1000
    
    # Analytics
    ANALYTICS_BATCH_SIZE: int = 100
    ANALYTICS_RETENTION_DAYS: int = 90
    
    # File Storage
    UPLOAD_DIR: str = "/tmp/traclearn/uploads"
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024  # 10MB
    ALLOWED_EXTENSIONS: List[str] = [
        ".pdf", ".doc", ".docx", ".txt", ".md",
        ".py", ".js", ".java", ".cpp", ".c",
        ".jpg", ".jpeg", ".png", ".gif",
        ".mp4", ".mp3", ".wav"
    ]
    
    # Voice Settings
    VOICE_ENABLED: bool = False
    VOICE_LANGUAGE: str = "en-US"
    
    # Monitoring
    SENTRY_DSN: Optional[str] = None
    PROMETHEUS_ENABLED: bool = True
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Create settings instance
settings = Settings()