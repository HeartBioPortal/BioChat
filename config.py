from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List
from functools import lru_cache

class Settings(BaseSettings):
    # API Keys
    openai_api_key: str
    ncbi_api_key: str
    
    # Contact Information
    contact_email: str
    
    # Server Configuration
    port: int = 8000
    host: str = "0.0.0.0"
    
    # Database Configuration
    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "biochat"
    db_user: str = "postgres"
    db_password: str = ""
    
    # Logging Configuration
    log_level: str = "INFO"
    log_format: str = "json"
    
    # Security Settings
    cors_origins: List[str] = ["http://localhost:3000"]
    api_key_header: str = "X-API-Key"
    rate_limit: int = 100
    
    # Feature Flags
    enable_cache: bool = True
    cache_ttl: int = 3600
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )

@lru_cache()
def get_settings() -> Settings:
    """Create cached settings instance"""
    return Settings()