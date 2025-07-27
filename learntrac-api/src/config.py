from pydantic_settings import BaseSettings
import os
from urllib.parse import urlparse, quote_plus

def fix_database_url(url: str) -> str:
    """Fix database URL with special characters in password"""
    if not url:
        return url
    
    # Convert postgres:// to postgresql:// for compatibility
    if url.startswith('postgres://'):
        url = url.replace('postgres://', 'postgresql://', 1)
    
    # Manual parsing for URLs with special characters that break urlparse
    if '://' in url and '@' in url:
        scheme_rest = url.split('://', 1)
        scheme = scheme_rest[0]
        rest = scheme_rest[1]
        
        userpass_host = rest.split('@', 1)
        if len(userpass_host) == 2:
            userpass = userpass_host[0]
            host_rest = userpass_host[1]
            
            if ':' in userpass:
                username = userpass.split(':', 1)[0]
                password = userpass.split(':', 1)[1]
                
                # Encode password if it has special characters
                if any(c in password for c in '{}[]()&%'):
                    password = quote_plus(password)
                
                # Rebuild URL
                url = f'{scheme}://{username}:{password}@{host_rest}'
    
    return url

def get_allowed_origins():
    """Get allowed origins from environment or defaults"""
    origins_str = os.getenv(
        "ALLOWED_ORIGINS",
        "http://localhost:8000,http://localhost:8001,http://localhost:3000"
    )
    return [origin.strip() for origin in origins_str.split(",")]

class Settings(BaseSettings):
    # Database
    database_url: str = fix_database_url(os.getenv("DATABASE_URL", "postgresql://user:pass@localhost/learntrac"))
    
    # Redis
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379")
    
    # Neo4j
    neo4j_uri: str = os.getenv("NEO4J_URI", "")
    neo4j_user: str = os.getenv("NEO4J_USERNAME", "neo4j")
    neo4j_password: str = os.getenv("NEO4J_PASSWORD", "")
    
    # Modern Authentication (Trac-based)
    trac_auth_secret: str = os.getenv("TRAC_AUTH_SECRET", "")
    trac_base_url: str = os.getenv("TRAC_BASE_URL", "http://localhost:8000")
    session_timeout: int = int(os.getenv("SESSION_TIMEOUT", "3600"))  # 1 hour
    
    # API Keys for service-to-service auth
    valid_api_keys: list = os.getenv("VALID_API_KEYS", "").split(",") if os.getenv("VALID_API_KEYS") else []
    internal_api_key: str = os.getenv("INTERNAL_API_KEY", "")
    
    # API Keys
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    
    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    # Environment
    environment: str = os.getenv("ENVIRONMENT", "development")
    
    class Config:
        env_file = ".env"
        extra = "ignore"  # Ignore extra environment variables

settings = Settings()