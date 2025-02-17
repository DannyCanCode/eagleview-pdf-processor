from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
from typing import Optional
import logging
import os

logger = logging.getLogger(__name__)

class Settings(BaseSettings):
    """Application settings with environment validation."""
    
    # Azure PostgreSQL configuration
    postgres_user: str
    postgres_password: str
    postgres_host: str
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
    
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        env_prefix="",
        extra="allow"
    )

@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    try:
        settings = Settings()
        logger.info("Settings loaded successfully")
        logger.info("Connection string length: %d", len(settings.azure_storage_connection_string) if settings.azure_storage_connection_string else 0)
        logger.info("Container name: %s", settings.azure_storage_container_name)
        return settings
    except Exception as e:
        logger.error("Error loading settings: %s", str(e))
        raise

# Configure logging
logging.basicConfig(level=logging.INFO)

# Export settings and getter
__all__ = ['get_settings'] 