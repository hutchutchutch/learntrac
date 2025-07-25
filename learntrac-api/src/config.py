from pydantic_settings import BaseSettings
from typing import List
import os

class Settings(BaseSettings):
    # Database
    database_url: str = os.getenv("DATABASE_URL", "postgresql://user:pass@localhost/learntrac")
    
    # Redis
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379")
    
    # Neo4j
    neo4j_uri: str = os.getenv("NEO4J_URI", "")
    neo4j_user: str = os.getenv("NEO4J_USER", "neo4j")
    neo4j_password: str = os.getenv("NEO4J_PASSWORD", "")
    
    # CORS
    allowed_origins: List[str] = [
        "http://localhost:8000",
        "http://localhost:8001",
        "http://localhost:3000",
    ]
    
    # AWS Cognito
    cognito_pool_id: str = os.getenv("COGNITO_POOL_ID", "")
    cognito_client_id: str = os.getenv("COGNITO_CLIENT_ID", "")
    aws_region: str = os.getenv("AWS_REGION", "us-east-2")
    
    # API Keys
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    
    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    # Environment
    environment: str = os.getenv("ENVIRONMENT", "development")
    
    class Config:
        env_file = ".env"

settings = Settings()