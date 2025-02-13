from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional

class Settings(BaseSettings):
    """Application settings with environment validation."""
    
    # Azure PostgreSQL configuration
    postgres_host: str
    postgres_user: str
    postgres_password: str
    postgres_db: str
    postgres_port: str = "5432"
    
    # API configuration
    api_title: str = "EagleView PDF Processor"
    api_version: str = "1.0.0"
    
    # Logging configuration
    log_level: str = "INFO"
    
    # Azure Blob Storage Configuration
    azure_storage_connection_string: str
    azure_storage_container_name: str = "pdf-files"
    
    class Config:
        env_file = ".env"
        case_sensitive = False

# Create settings instance
settings = Settings()

# Export settings
__all__ = ['settings'] 